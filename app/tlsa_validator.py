import hashlib
import logging
import socket
import ssl
import time
from datetime import datetime, timezone

import dns.resolver
import dns.name
import dns.rdatatype
import dns.exception
from cryptography import x509
from cryptography.hazmat.primitives import serialization


class TLSAValidator:
    """
    TLSA (Transport Layer Security Authentication) record validator
    implementing DANE (DNS-Based Authentication of Named Entities) checking.
    """

    def __init__(self, domain):
        self.domain = domain
        self.domain_name = dns.name.from_text(domain)

        # TLSA record certificate usage types
        self.cert_usage_types = {
            0: "PKIX-TA",  # CA constraint
            1: "PKIX-EE",  # Service certificate constraint
            2: "DANE-TA",  # Trust anchor assertion
            3: "DANE-EE",  # Domain-issued certificate
        }

        # TLSA record selector types
        self.selector_types = {
            0: "Cert",  # Full certificate
            1: "SPKI",  # Subject Public Key Info
        }

        # TLSA record matching types
        self.matching_types = {
            0: "Full",  # No hash, full data
            1: "SHA-256",  # SHA-256 hash
            2: "SHA-512",  # SHA-512 hash
        }

    def validate_tlsa(self, port=443, protocol="tcp", timeout=10):
        """
        Validate TLSA records for the domain.
        Returns comprehensive TLSA validation results.
        """
        start_time = time.time()

        result = {
            "domain": self.domain,
            "port": port,
            "protocol": protocol,
            "tlsa_status": "unknown",
            "tlsa_records": [],
            "certificate_info": None,
            "dane_validation": {
                "valid_associations": [],
                "invalid_associations": [],
                "status": "unknown",
            },
            "validation_time": datetime.utcnow().isoformat(),
            "errors": [],
            "warnings": [],
            "query_time_ms": 0,
            "connect_time_ms": 0,
        }

        try:
            # Step 1: Query TLSA records
            tlsa_records = self._query_tlsa_records(port, protocol)
            query_time = time.time()
            result["query_time_ms"] = round((query_time - start_time) * 1000, 2)

            if not tlsa_records:
                result["tlsa_status"] = "no_records"
                result["warnings"].append(
                    f"No TLSA records found for _{port}._{protocol}.{self.domain}"
                )
                return result

            result["tlsa_records"] = tlsa_records
            result["tlsa_status"] = "records_found"

            # Step 2: Retrieve TLS certificate from server
            try:
                cert_info = self._get_tls_certificate(port, timeout)
                connect_time = time.time()
                result["connect_time_ms"] = round((connect_time - query_time) * 1000, 2)

                result["certificate_info"] = cert_info

                # Step 3: Validate each TLSA record against the certificate
                validation_results = self._validate_dane_associations(
                    tlsa_records, cert_info
                )
                result["dane_validation"] = validation_results

                # Determine overall DANE status
                if validation_results["valid_associations"]:
                    result["tlsa_status"] = "valid"
                elif validation_results["invalid_associations"]:
                    result["tlsa_status"] = "invalid"
                else:
                    result["tlsa_status"] = "no_matches"

            except Exception as e:
                result["errors"].append(f"TLS certificate retrieval failed: {str(e)}")
                result["tlsa_status"] = "cert_unavailable"

        except Exception as e:
            result["errors"].append(f"TLSA validation failed: {str(e)}")
            result["tlsa_status"] = "error"

        return result

    def _query_tlsa_records(self, port, protocol):
        """Query TLSA records from DNS"""
        tlsa_records = []

        try:
            # Construct TLSA record name: _port._protocol.domain
            tlsa_name = f"_{port}._{protocol}.{self.domain}"

            resolver = dns.resolver.Resolver()
            resolver.use_edns(0, dns.flags.DO)  # Enable DNSSEC

            answer = resolver.resolve(tlsa_name, "TLSA")

            for rr in answer.rrset:
                tlsa_record = {
                    "name": tlsa_name,
                    "usage": rr.usage,
                    "usage_description": self.cert_usage_types.get(
                        rr.usage, f"Unknown ({rr.usage})"
                    ),
                    "selector": rr.selector,
                    "selector_description": self.selector_types.get(
                        rr.selector, f"Unknown ({rr.selector})"
                    ),
                    "mtype": rr.mtype,
                    "mtype_description": self.matching_types.get(
                        rr.mtype, f"Unknown ({rr.mtype})"
                    ),
                    "cert_assoc_data": rr.cert.hex(),
                    "cert_assoc_data_length": len(rr.cert),
                    "ttl": answer.rrset.ttl,
                }
                tlsa_records.append(tlsa_record)

            logging.info(f"Found {len(tlsa_records)} TLSA records for {tlsa_name}")
            return tlsa_records

        except dns.resolver.NXDOMAIN:
            logging.info(f"No TLSA records found for _{port}._{protocol}.{self.domain}")
            return []
        except dns.resolver.NoAnswer:
            logging.info(
                f"TLSA query returned no answer for _{port}._{protocol}.{self.domain}"
            )
            return []
        except Exception as e:
            logging.error(f"Error querying TLSA records: {e}")
            raise

    def _get_tls_certificate(self, port, timeout):
        """Retrieve TLS certificate from the server"""
        try:
            # Create SSL context with secure TLS settings
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE

            # Enforce minimum TLS version 1.2 for security
            context.minimum_version = ssl.TLSVersion.TLSv1_2

            # Connect and get certificate
            with socket.create_connection((self.domain, port), timeout=timeout) as sock:
                with context.wrap_socket(sock, server_hostname=self.domain) as ssock:
                    # Get certificate chain
                    cert_der = ssock.getpeercert(binary_form=True)
                    cert_chain = ssock.getpeercert_chain()

            # Parse certificate using cryptography library
            cert = x509.load_der_x509_certificate(cert_der)

            # Extract certificate information
            cert_info = {
                "subject": cert.subject.rfc4514_string(),
                "issuer": cert.issuer.rfc4514_string(),
                "serial_number": str(cert.serial_number),
                "not_valid_before": cert.not_valid_before.isoformat(),
                "not_valid_after": cert.not_valid_after.isoformat(),
                "signature_algorithm": cert.signature_algorithm_oid._name,
                "public_key_algorithm": cert.public_key().__class__.__name__,
                "der_data": cert_der,
                "pem_data": cert.public_bytes(serialization.Encoding.PEM).decode(),
                "public_key_info": None,
                "fingerprints": {},
                "chain_length": len(cert_chain) if cert_chain else 1,
            }

            # Get public key info
            public_key = cert.public_key()
            spki_der = public_key.public_bytes(
                encoding=serialization.Encoding.DER,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
            cert_info["public_key_info"] = spki_der

            # Calculate fingerprints
            cert_info["fingerprints"] = {
                "sha256": hashlib.sha256(cert_der).hexdigest(),
                "sha512": hashlib.sha512(cert_der).hexdigest(),
                "spki_sha256": hashlib.sha256(spki_der).hexdigest(),
                "spki_sha512": hashlib.sha512(spki_der).hexdigest(),
            }

            # Subject Alternative Names
            try:
                san_ext = cert.extensions.get_extension_for_oid(
                    x509.ExtensionOID.SUBJECT_ALTERNATIVE_NAME
                )
                cert_info["san"] = [name.value for name in san_ext.value]
            except x509.ExtensionNotFound:
                cert_info["san"] = []

            logging.info(f"Retrieved TLS certificate for {self.domain}:{port}")
            return cert_info

        except Exception as e:
            logging.error(f"Error retrieving TLS certificate: {e}")
            raise

    def _validate_dane_associations(self, tlsa_records, cert_info):
        """Validate DANE certificate associations"""
        validation_result = {
            "valid_associations": [],
            "invalid_associations": [],
            "status": "unknown",
            "summary": {},
        }

        for tlsa_record in tlsa_records:
            association_result = self._validate_single_association(
                tlsa_record, cert_info
            )

            if association_result["valid"]:
                validation_result["valid_associations"].append(association_result)
            else:
                validation_result["invalid_associations"].append(association_result)

        # Determine overall status
        valid_count = len(validation_result["valid_associations"])
        invalid_count = len(validation_result["invalid_associations"])
        total_count = valid_count + invalid_count

        if valid_count > 0:
            validation_result["status"] = "valid"
        elif invalid_count > 0:
            validation_result["status"] = "invalid"
        else:
            validation_result["status"] = "no_associations"

        validation_result["summary"] = {
            "total_records": total_count,
            "valid_associations": valid_count,
            "invalid_associations": invalid_count,
            "success_rate": (
                round((valid_count / total_count) * 100, 1) if total_count > 0 else 0
            ),
        }

        return validation_result

    def _validate_single_association(self, tlsa_record, cert_info):
        """Validate a single TLSA record against the certificate"""
        result = {
            "tlsa_record": tlsa_record,
            "valid": False,
            "reason": "",
            "computed_hash": "",
            "expected_hash": tlsa_record["cert_assoc_data"],
            "match_details": {},
        }

        try:
            # Get the data to hash based on selector
            if tlsa_record["selector"] == 0:  # Full certificate
                data_to_hash = cert_info["der_data"]
                result["match_details"]["data_source"] = "full_certificate"
            elif tlsa_record["selector"] == 1:  # Subject Public Key Info
                data_to_hash = cert_info["public_key_info"]
                result["match_details"]["data_source"] = "public_key_info"
            else:
                result["reason"] = (
                    f"Unsupported selector type: {tlsa_record['selector']}"
                )
                return result

            # Apply matching type (hashing)
            if tlsa_record["mtype"] == 0:  # Full data, no hashing
                computed_data = data_to_hash.hex()
            elif tlsa_record["mtype"] == 1:  # SHA-256
                computed_data = hashlib.sha256(data_to_hash).hexdigest()
            elif tlsa_record["mtype"] == 2:  # SHA-512
                computed_data = hashlib.sha512(data_to_hash).hexdigest()
            else:
                result["reason"] = f"Unsupported matching type: {tlsa_record['mtype']}"
                return result

            result["computed_hash"] = computed_data
            result["match_details"]["hash_algorithm"] = self.matching_types.get(
                tlsa_record["mtype"], "Unknown"
            )
            result["match_details"]["data_length"] = len(data_to_hash)

            # Compare with TLSA record
            if computed_data.lower() == tlsa_record["cert_assoc_data"].lower():
                result["valid"] = True
                result["reason"] = "Certificate association matches TLSA record"
            else:
                result["valid"] = False
                result["reason"] = "Certificate association does not match TLSA record"

        except Exception as e:
            result["reason"] = f"Validation error: {str(e)}"

        return result

    def get_detailed_analysis(self, port=443, protocol="tcp", timeout=10):
        """Get detailed TLSA analysis with troubleshooting information"""
        basic_result = self.validate_tlsa(port, protocol, timeout)

        detailed_result = {
            **basic_result,
            "detailed_analysis": {
                "tlsa_record_analysis": [],
                "certificate_analysis": {},
                "security_assessment": {},
                "troubleshooting": [],
                "recommendations": [],
                "compatibility_notes": [],
            },
        }

        try:
            # Analyze each TLSA record in detail
            self._analyze_tlsa_records(detailed_result)

            # Analyze certificate properties
            self._analyze_certificate(detailed_result)

            # Security assessment
            self._assess_security(detailed_result)

            # Generate troubleshooting guidance
            self._generate_tlsa_troubleshooting(detailed_result)

            # Generate recommendations
            self._generate_tlsa_recommendations(detailed_result)

        except Exception as e:
            detailed_result["detailed_analysis"]["errors"] = [
                f"Detailed analysis error: {str(e)}"
            ]

        return detailed_result

    def _analyze_tlsa_records(self, result):
        """Detailed analysis of TLSA records"""
        analysis = []

        for tlsa_record in result["tlsa_records"]:
            record_analysis = {
                "record": tlsa_record,
                "usage_analysis": self._analyze_usage_type(tlsa_record["usage"]),
                "selector_analysis": self._analyze_selector_type(
                    tlsa_record["selector"]
                ),
                "matching_analysis": self._analyze_matching_type(tlsa_record["mtype"]),
                "security_notes": [],
            }

            # Add security notes based on record properties
            if tlsa_record["usage"] in [0, 1]:  # PKIX
                record_analysis["security_notes"].append(
                    "Uses PKIX validation - requires valid CA chain"
                )
            elif tlsa_record["usage"] in [2, 3]:  # DANE
                record_analysis["security_notes"].append(
                    "Uses DANE validation - bypasses traditional CA validation"
                )

            if tlsa_record["mtype"] == 0:
                record_analysis["security_notes"].append(
                    "Full data matching - larger DNS records but precise matching"
                )
            elif tlsa_record["mtype"] in [1, 2]:
                record_analysis["security_notes"].append(
                    "Hash-based matching - smaller DNS records, cryptographically secure"
                )

            analysis.append(record_analysis)

        result["detailed_analysis"]["tlsa_record_analysis"] = analysis

    def _analyze_usage_type(self, usage):
        """Analyze TLSA usage type"""
        analysis = {
            "type": usage,
            "name": self.cert_usage_types.get(usage, f"Unknown ({usage})"),
            "description": "",
            "security_implications": "",
            "recommended": True,
        }

        if usage == 0:  # PKIX-TA
            analysis["description"] = (
                "CA constraint - certificate must validate via traditional PKIX and match the association"
            )
            analysis["security_implications"] = (
                "Provides additional security on top of traditional CA validation"
            )
        elif usage == 1:  # PKIX-EE
            analysis["description"] = (
                "Service certificate constraint - end entity cert must validate via PKIX and match"
            )
            analysis["security_implications"] = (
                "Pins specific certificate while maintaining CA validation"
            )
        elif usage == 2:  # DANE-TA
            analysis["description"] = (
                "Trust anchor assertion - certificate must chain to the specified trust anchor"
            )
            analysis["security_implications"] = (
                "Bypasses traditional CAs, uses DNS-specified trust anchor"
            )
            analysis["recommended"] = False  # More complex to implement correctly
        elif usage == 3:  # DANE-EE
            analysis["description"] = (
                "Domain-issued certificate - certificate must match exactly"
            )
            analysis["security_implications"] = (
                "Complete bypass of CA system, DNS is the only trust source"
            )
            analysis["recommended"] = True  # Simple and effective
        else:
            analysis["recommended"] = False
            analysis["security_implications"] = (
                "Unknown usage type - may not be supported by validators"
            )

        return analysis

    def _analyze_selector_type(self, selector):
        """Analyze TLSA selector type"""
        analysis = {
            "type": selector,
            "name": self.selector_types.get(selector, f"Unknown ({selector})"),
            "description": "",
            "advantages": [],
            "disadvantages": [],
        }

        if selector == 0:  # Full certificate
            analysis["description"] = "Matches against the complete certificate"
            analysis["advantages"] = [
                "Precise matching",
                "No ambiguity about which certificate",
            ]
            analysis["disadvantages"] = [
                "Larger DNS records",
                "Must update DNS when certificate changes",
            ]
        elif selector == 1:  # SPKI
            analysis["description"] = "Matches against the Subject Public Key Info"
            analysis["advantages"] = [
                "Smaller DNS records",
                "Can survive certificate renewal with same key",
            ]
            analysis["disadvantages"] = ["Less precise than full certificate matching"]

        return analysis

    def _analyze_matching_type(self, mtype):
        """Analyze TLSA matching type"""
        analysis = {
            "type": mtype,
            "name": self.matching_types.get(mtype, f"Unknown ({mtype})"),
            "description": "",
            "hash_algorithm": None,
            "security_strength": "unknown",
        }

        if mtype == 0:
            analysis["description"] = "Full data - no hashing applied"
            analysis["security_strength"] = "high"
        elif mtype == 1:
            analysis["description"] = "SHA-256 hash of the certificate data"
            analysis["hash_algorithm"] = "SHA-256"
            analysis["security_strength"] = "high"
        elif mtype == 2:
            analysis["description"] = "SHA-512 hash of the certificate data"
            analysis["hash_algorithm"] = "SHA-512"
            analysis["security_strength"] = "very_high"

        return analysis

    def _analyze_certificate(self, result):
        """Analyze the TLS certificate"""
        if not result["certificate_info"]:
            return

        cert_info = result["certificate_info"]
        analysis = {
            "validity_period": {},
            "key_strength": {},
            "extensions": {},
            "compatibility": {},
        }

        # Validity analysis
        not_before = datetime.fromisoformat(
            cert_info["not_valid_before"].replace("Z", "+00:00")
        )
        not_after = datetime.fromisoformat(
            cert_info["not_valid_after"].replace("Z", "+00:00")
        )
        now = datetime.now(timezone.utc)

        analysis["validity_period"] = {
            "valid_from": cert_info["not_valid_before"],
            "valid_until": cert_info["not_valid_after"],
            "days_remaining": (not_after - now).days,
            "currently_valid": not_before <= now <= not_after,
        }

        # Key strength analysis
        analysis["key_strength"] = {
            "algorithm": cert_info["public_key_algorithm"],
            "signature_algorithm": cert_info["signature_algorithm"],
        }

        # SAN analysis
        analysis["extensions"] = {
            "subject_alternative_names": cert_info.get("san", []),
            "san_count": len(cert_info.get("san", [])),
        }

        result["detailed_analysis"]["certificate_analysis"] = analysis

    def _assess_security(self, result):
        """Assess overall DANE security implementation"""
        assessment = {
            "overall_score": 0,
            "strengths": [],
            "weaknesses": [],
            "risk_factors": [],
        }

        # Scoring based on various factors
        score = 0

        if result["tlsa_status"] == "valid":
            score += 40
            assessment["strengths"].append("TLSA records validate successfully")
        elif result["tlsa_status"] == "invalid":
            assessment["weaknesses"].append("TLSA validation failed")
        elif result["tlsa_status"] == "no_records":
            assessment["weaknesses"].append(
                "No TLSA records found - DANE not implemented"
            )

        # Check for modern hash algorithms
        for record in result["tlsa_records"]:
            if record["mtype"] in [1, 2]:  # SHA-256 or SHA-512
                score += 10
                assessment["strengths"].append(
                    f"Uses cryptographically strong hashing: {record['mtype_description']}"
                )
            elif record["mtype"] == 0:
                score += 5
                assessment["strengths"].append(
                    "Uses full certificate matching - high precision"
                )

        # Check for DANE-EE usage (most secure)
        for record in result["tlsa_records"]:
            if record["usage"] == 3:  # DANE-EE
                score += 15
                assessment["strengths"].append(
                    "Uses DANE-EE - bypasses CA system completely"
                )

        # Certificate validity
        if result["certificate_info"]:
            cert_analysis = result["detailed_analysis"].get("certificate_analysis", {})
            validity = cert_analysis.get("validity_period", {})

            if validity.get("currently_valid"):
                score += 20
                assessment["strengths"].append("Certificate is currently valid")

                days_remaining = validity.get("days_remaining", 0)
                if days_remaining > 30:
                    score += 5
                elif days_remaining > 0:
                    assessment["risk_factors"].append(
                        f"Certificate expires in {days_remaining} days"
                    )
                else:
                    score -= 20
                    assessment["weaknesses"].append("Certificate has expired")
            else:
                assessment["weaknesses"].append("Certificate is not currently valid")

        assessment["overall_score"] = min(100, max(0, score))
        result["detailed_analysis"]["security_assessment"] = assessment

    def _generate_tlsa_troubleshooting(self, result):
        """Generate TLSA-specific troubleshooting guidance"""
        troubleshooting = []

        if result["tlsa_status"] == "no_records":
            troubleshooting.extend(
                [
                    "🔍 Issue: No TLSA records found",
                    "💡 Solution: Implement DANE by creating TLSA records",
                    "📋 Steps:",
                    "   1. Generate TLSA record using your certificate",
                    "   2. Publish record as _443._tcp.yourdomain.com",
                    "   3. Verify DNS propagation",
                    "   4. Test with DANE validators",
                ]
            )

        elif result["tlsa_status"] == "cert_unavailable":
            troubleshooting.extend(
                [
                    "🔍 Issue: Cannot retrieve TLS certificate from server",
                    "💡 Solution: Verify server configuration and connectivity",
                    "📋 Check:",
                    "   - Server is running and accessible",
                    "   - Correct port is specified",
                    "   - Firewall allows connections",
                    "   - TLS is properly configured",
                ]
            )

        elif result["tlsa_status"] == "invalid":
            troubleshooting.extend(
                [
                    "🔍 Issue: TLSA records do not match certificate",
                    "💡 Solution: Update TLSA records or certificate",
                    "📋 Common causes:",
                    "   - Certificate was renewed but TLSA not updated",
                    "   - Wrong certificate data used to generate TLSA",
                    "   - Incorrect usage/selector/matching type values",
                ]
            )

        # Add specific issues found in validation
        for invalid_assoc in result["dane_validation"].get("invalid_associations", []):
            tlsa = invalid_assoc["tlsa_record"]
            troubleshooting.append(
                f"❌ TLSA record (usage:{tlsa['usage']}, selector:{tlsa['selector']}, type:{tlsa['mtype']}): {invalid_assoc['reason']}"
            )

        result["detailed_analysis"]["troubleshooting"] = troubleshooting

    def _generate_tlsa_recommendations(self, result):
        """Generate DANE implementation recommendations"""
        recommendations = []

        if result["tlsa_status"] == "valid":
            recommendations.append(
                "✅ DANE validation successful - excellent security posture"
            )

        # Record type recommendations
        usage_3_found = any(r["usage"] == 3 for r in result["tlsa_records"])
        if usage_3_found:
            recommendations.append("✅ DANE-EE (usage 3) provides strongest security")
        else:
            recommendations.append("💡 Consider DANE-EE (usage 3) for maximum security")

        # Hash algorithm recommendations
        modern_hash = any(r["mtype"] in [1, 2] for r in result["tlsa_records"])
        if modern_hash:
            recommendations.append(
                "✅ Modern hash algorithms (SHA-256/SHA-512) detected"
            )
        else:
            recommendations.append(
                "🔄 Consider using SHA-256 or SHA-512 for better security"
            )

        # Certificate management
        if result["certificate_info"]:
            cert_analysis = result["detailed_analysis"].get("certificate_analysis", {})
            days_remaining = cert_analysis.get("validity_period", {}).get(
                "days_remaining", 0
            )

            if days_remaining < 30:
                recommendations.append(
                    "⏰ Plan certificate renewal and TLSA record updates"
                )

        # General DANE recommendations
        recommendations.extend(
            [
                "🔄 Implement automated TLSA record management",
                "📊 Monitor DANE validation regularly",
                "🛡️ Use DNSSEC to secure TLSA records",
                "📋 Document TLSA record management procedures",
            ]
        )

        result["detailed_analysis"]["recommendations"] = recommendations
