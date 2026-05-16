"""
CAA (Certification Authority Authorization) record validator.

Implements CAA record validation per RFC 8659, including tree-climbing
to find inherited CAA records when none exist on the target domain.
"""

import logging
import time
from datetime import datetime

import dns.resolver
import dns.name
import dns.rdatatype
import dns.exception

# Known CAA tags defined by RFC 8659 and IANA registry.
KNOWN_CAA_TAGS = {"issue", "issuewild", "iodef", "contactemail", "contactphone"}

# Tags relevant to certificate issuance authorization.
ISSUANCE_TAGS = {"issue", "issuewild"}


class CAAValidator:
    """
    CAA (Certification Authority Authorization) record validator.

    Queries CAA records for a domain, walks up the DNS tree per RFC 8659
    when no CAA records exist on the target, and produces a structured
    validation result describing which CAs are authorized to issue
    certificates for the domain.
    """

    def __init__(self, domain):
        self.domain = domain.rstrip(".")
        self.domain_name = dns.name.from_text(self.domain)

    def validate_caa(self, timeout=10, max_levels=10):
        """
        Validate CAA records for the domain.

        Performs RFC 8659 tree-climbing search: if the target domain has
        no CAA records, parent domains are queried until a record is found
        or the root is reached.

        Args:
            timeout: DNS query timeout in seconds.
            max_levels: Maximum tree-climb iterations (safety bound).

        Returns:
            A dictionary with caa_status, caa_records, authorized_cas,
            wildcard_authorized_cas, iodef_targets, errors/warnings and timing.
        """
        start_time = time.time()

        result = {
            "domain": self.domain,
            "caa_status": "unknown",
            "caa_records": [],
            "authorized_cas": [],
            "wildcard_authorized_cas": [],
            "iodef_targets": [],
            "issuance_allowed": True,
            "wildcard_issuance_allowed": True,
            "checked_domain": None,
            "inherited": False,
            "validation_time": datetime.utcnow().isoformat(),
            "errors": [],
            "warnings": [],
            "query_time_ms": 0,
        }

        try:
            records, checked_domain, inherited = self._query_caa_with_inheritance(
                timeout=timeout, max_levels=max_levels
            )
            result["query_time_ms"] = round((time.time() - start_time) * 1000, 2)
            result["checked_domain"] = checked_domain
            result["inherited"] = inherited

            if not records:
                result["caa_status"] = "no_records"
                result["warnings"].append(
                    f"No CAA records found for {self.domain} or any parent zone"
                )
                return result

            result["caa_records"] = records

            # Analyse and summarise records.
            analysis = self._analyze_records(records)
            result["authorized_cas"] = analysis["authorized_cas"]
            result["wildcard_authorized_cas"] = analysis["wildcard_authorized_cas"]
            result["iodef_targets"] = analysis["iodef_targets"]
            result["issuance_allowed"] = analysis["issuance_allowed"]
            result["wildcard_issuance_allowed"] = analysis["wildcard_issuance_allowed"]

            # Validate record syntax and accumulate warnings.
            syntax_warnings = self._validate_syntax(records)
            result["warnings"].extend(syntax_warnings)

            if analysis["issuance_allowed"] and analysis["authorized_cas"]:
                result["caa_status"] = "valid"
            elif not analysis["issuance_allowed"]:
                result["caa_status"] = "restricted"
            else:
                # Records exist but no issue/issuewild semantics extracted.
                result["caa_status"] = "records_found"

        except Exception as exc:  # noqa: BLE001 - keep validation non-fatal
            result["errors"].append(f"CAA validation failed: {str(exc)}")
            result["caa_status"] = "error"

        return result

    def _query_caa_with_inheritance(self, timeout=10, max_levels=10):
        """
        Query CAA records for the domain, climbing the DNS tree if absent.

        Per RFC 8659 section 3, if a domain has no CAA record set, the
        validator MUST walk up the tree until a record set is found or
        the root is reached.

        Returns:
            (records, checked_domain, inherited) tuple.
        """
        current = self.domain_name
        inherited = False
        levels = 0

        while levels < max_levels:
            try:
                records = self._query_caa_records(current.to_text(), timeout=timeout)
            except dns.exception.DNSException as exc:
                logging.warning(f"CAA query error for {current.to_text()}: {exc}")
                records = []

            if records:
                return records, current.to_text(omit_final_dot=True), inherited

            # Climb up one label.
            if current == dns.name.root:
                break
            try:
                parent = current.parent()
            except dns.name.NoParent:
                break

            if parent == current:
                break

            current = parent
            inherited = True
            levels += 1

        return [], current.to_text(omit_final_dot=True), inherited

    def _query_caa_records(self, domain, timeout=10):
        """Query CAA records for a specific domain."""
        records = []
        try:
            resolver = dns.resolver.Resolver()
            resolver.lifetime = timeout
            resolver.timeout = timeout
            resolver.use_edns(0, dns.flags.DO)

            answer = resolver.resolve(domain, "CAA")

            for rr in answer.rrset:
                tag = self._decode_tag(rr.tag)
                value = self._decode_value(rr.value)
                record = {
                    "name": domain.rstrip("."),
                    "flags": int(rr.flags),
                    "critical": bool(int(rr.flags) & 0x80),
                    "tag": tag,
                    "value": value,
                    "ttl": answer.rrset.ttl,
                }
                records.append(record)

            logging.info(f"Found {len(records)} CAA records for {domain}")
            return records

        except dns.resolver.NXDOMAIN:
            logging.debug(f"NXDOMAIN for CAA query on {domain}")
            return []
        except dns.resolver.NoAnswer:
            logging.debug(f"No CAA records for {domain}")
            return []
        except dns.resolver.NoNameservers as exc:
            logging.warning(f"No nameservers responded for CAA on {domain}: {exc}")
            return []
        except dns.exception.Timeout:
            logging.warning(f"Timeout querying CAA records for {domain}")
            return []

    @staticmethod
    def _decode_tag(tag):
        """Decode CAA tag which dnspython returns as bytes."""
        if isinstance(tag, bytes):
            try:
                return tag.decode("ascii").lower()
            except UnicodeDecodeError:
                return tag.decode("ascii", errors="replace").lower()
        return str(tag).lower()

    @staticmethod
    def _decode_value(value):
        """Decode CAA value which dnspython returns as bytes."""
        if isinstance(value, bytes):
            try:
                return value.decode("utf-8")
            except UnicodeDecodeError:
                return value.decode("utf-8", errors="replace")
        return str(value)

    def _analyze_records(self, records):
        """Extract authorized CAs, IODEF targets, and issuance posture."""
        authorized_cas = []
        wildcard_authorized_cas = []
        iodef_targets = []

        explicit_issue = False
        explicit_issuewild = False

        # Whether any issue/issuewild record allows issuance.
        issue_permits = False
        issuewild_permits = False

        for record in records:
            tag = record["tag"]
            raw_value = record["value"]
            value = raw_value.strip()

            if tag == "issue":
                explicit_issue = True
                ca = self._extract_ca_name(value)
                if ca:
                    authorized_cas.append(
                        {
                            "ca": ca,
                            "raw_value": raw_value,
                            "critical": record["critical"],
                        }
                    )
                    issue_permits = True
                # A bare ";" means no CA is permitted to issue.

            elif tag == "issuewild":
                explicit_issuewild = True
                ca = self._extract_ca_name(value)
                if ca:
                    wildcard_authorized_cas.append(
                        {
                            "ca": ca,
                            "raw_value": raw_value,
                            "critical": record["critical"],
                        }
                    )
                    issuewild_permits = True

            elif tag == "iodef":
                iodef_targets.append({"target": value, "critical": record["critical"]})

        # RFC 8659: if no issue tag is present, issuance is implicitly allowed.
        # If issue records are present, at least one must permit a CA.
        issuance_allowed = (not explicit_issue) or issue_permits

        # Wildcard issuance defaults to issue policy unless issuewild present.
        if explicit_issuewild:
            wildcard_issuance_allowed = issuewild_permits
        else:
            wildcard_issuance_allowed = issuance_allowed
            # When issue allows a CA, the same CAs are authorized for wildcards
            # absent an explicit issuewild record.
            if issuance_allowed and not wildcard_authorized_cas:
                wildcard_authorized_cas = list(authorized_cas)

        return {
            "authorized_cas": authorized_cas,
            "wildcard_authorized_cas": wildcard_authorized_cas,
            "iodef_targets": iodef_targets,
            "issuance_allowed": issuance_allowed,
            "wildcard_issuance_allowed": wildcard_issuance_allowed,
        }

    @staticmethod
    def _extract_ca_name(value):
        """
        Extract the CA domain from an issue/issuewild value.

        Per RFC 8659, the value is "<issuer-domain>[;param=value...]".
        A bare ";" or empty value means no CA is authorized.
        """
        if not value or value.strip() == ";":
            return None

        ca = value.split(";", 1)[0].strip()
        return ca if ca else None

    def _validate_syntax(self, records):
        """Validate CAA record syntax and return any warnings."""
        warnings = []

        for record in records:
            tag = record["tag"]
            flags = record["flags"]

            if tag not in KNOWN_CAA_TAGS:
                warnings.append(f"Unknown CAA tag '{tag}' on {record['name']}")

            # Flags is an 8-bit field. Only the high bit (0x80) is defined
            # as the critical flag. Other bits SHOULD be zero.
            if flags & ~0x80:
                warnings.append(
                    f"Reserved CAA flag bits set on {record['name']} (flags={flags})"
                )

            if tag in ISSUANCE_TAGS and record["value"] is None:
                warnings.append(f"Empty value for {tag} record on {record['name']}")

        return warnings

    def get_detailed_analysis(self, timeout=10, max_levels=10):
        """Get detailed CAA analysis with security assessment and recommendations."""
        basic_result = self.validate_caa(timeout=timeout, max_levels=max_levels)

        detailed_result = {
            **basic_result,
            "detailed_analysis": {
                "record_analysis": [],
                "security_assessment": {},
                "recommendations": [],
                "troubleshooting": [],
            },
        }

        try:
            self._analyze_individual_records(detailed_result)
            self._assess_security(detailed_result)
            self._generate_recommendations(detailed_result)
            self._generate_troubleshooting(detailed_result)
        except Exception as exc:  # noqa: BLE001
            detailed_result["detailed_analysis"]["errors"] = [
                f"Detailed CAA analysis error: {str(exc)}"
            ]

        return detailed_result

    def _analyze_individual_records(self, result):
        """Add per-record analysis for detailed output."""
        analyses = []
        for record in result["caa_records"]:
            record_analysis = {
                "record": record,
                "purpose": self._describe_tag(record["tag"]),
                "is_known_tag": record["tag"] in KNOWN_CAA_TAGS,
                "is_critical": record["critical"],
            }
            analyses.append(record_analysis)
        result["detailed_analysis"]["record_analysis"] = analyses

    @staticmethod
    def _describe_tag(tag):
        """Return a human-readable purpose string for a CAA tag."""
        descriptions = {
            "issue": "Authorizes a CA to issue regular certificates",
            "issuewild": "Authorizes a CA to issue wildcard certificates",
            "iodef": "Reporting endpoint for policy violations",
            "contactemail": "Contact email address (extension)",
            "contactphone": "Contact phone number (extension)",
        }
        return descriptions.get(tag, f"Unknown tag: {tag}")

    def _assess_security(self, result):
        """Assess CAA security posture and assign a score."""
        assessment = {
            "overall_score": 0,
            "strengths": [],
            "weaknesses": [],
        }

        score = 0

        if result["caa_status"] == "valid":
            score += 40
            assessment["strengths"].append(
                "CAA records authorize specific Certificate Authorities"
            )
        elif result["caa_status"] == "restricted":
            score += 50
            assessment["strengths"].append(
                "CAA records explicitly forbid certificate issuance"
            )
        elif result["caa_status"] == "no_records":
            assessment["weaknesses"].append(
                "No CAA records found - any CA may issue certificates"
            )

        # Inheritance is informational, not a strength or weakness on its own.
        if result["inherited"] and result["caa_records"]:
            assessment["strengths"].append(
                f"CAA policy inherited from parent zone {result['checked_domain']}"
            )

        # Wildcard handling.
        if result["wildcard_authorized_cas"]:
            score += 10
            assessment["strengths"].append("Wildcard issuance policy defined")
        elif result["caa_records"] and not result["wildcard_issuance_allowed"]:
            score += 10
            assessment["strengths"].append(
                "Wildcard certificate issuance is restricted"
            )

        # IODEF reporting.
        if result["iodef_targets"]:
            score += 10
            assessment["strengths"].append(
                "IODEF reporting endpoint configured for policy violations"
            )
        elif result["caa_records"]:
            assessment["weaknesses"].append("No IODEF reporting endpoint configured")

        # Critical flag use - encourages strict enforcement.
        if any(r["critical"] for r in result["caa_records"]):
            score += 5
            assessment["strengths"].append(
                "At least one CAA record uses the critical flag"
            )

        if result["errors"]:
            assessment["weaknesses"].extend(result["errors"])

        assessment["overall_score"] = min(100, max(0, score))
        result["detailed_analysis"]["security_assessment"] = assessment

    def _generate_recommendations(self, result):
        """Generate actionable CAA recommendations."""
        recommendations = []

        if result["caa_status"] == "no_records":
            recommendations.extend(
                [
                    "Add CAA records to restrict which CAs may issue certificates",
                    "Example: '0 issue \"letsencrypt.org\"' to authorize Let's Encrypt",
                    "Use DNSSEC to protect CAA records from tampering",
                ]
            )
        else:
            if not result["iodef_targets"]:
                recommendations.append(
                    "Add an 'iodef' record to receive notifications of policy violations"
                )
            if (
                not result["wildcard_authorized_cas"]
                and result["wildcard_issuance_allowed"]
            ):
                recommendations.append(
                    "Consider adding an explicit 'issuewild' record for wildcard issuance policy"
                )
            recommendations.append(
                "Regularly review authorized CAs to match your actual issuance practices"
            )
            recommendations.append(
                "Keep CAA records protected by DNSSEC to prevent downgrade attacks"
            )

        result["detailed_analysis"]["recommendations"] = recommendations

    def _generate_troubleshooting(self, result):
        """Generate troubleshooting guidance for common CAA misconfigurations."""
        troubleshooting = []

        if result["caa_status"] == "error":
            troubleshooting.append(
                "CAA query failed - verify DNS resolver connectivity"
            )

        if result["caa_records"]:
            # Detect issue records that disallow everything via bare ";".
            blockers = [
                r
                for r in result["caa_records"]
                if r["tag"] in ISSUANCE_TAGS and r["value"].strip() == ";"
            ]
            if blockers:
                troubleshooting.append(
                    "One or more records use ';' to forbid all CA issuance - "
                    "no certificates can be issued by any CA"
                )

        for warning in result["warnings"]:
            troubleshooting.append(f"Warning: {warning}")

        result["detailed_analysis"]["troubleshooting"] = troubleshooting
