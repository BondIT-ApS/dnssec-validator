import dns.resolver
import dns.dnssec
import dns.name
import dns.rdatatype
import dns.rdataclass
import dns.rrset
import dns.query
import dns.message
from datetime import datetime, timezone
import logging
import time
import hashlib
import base64

class DNSSECValidator:
    def __init__(self, domain):
        self.domain = domain
        self.domain_name = dns.name.from_text(domain)
        self.results = {
            'domain': domain,
            'status': 'unknown',
            'validation_time': datetime.utcnow().isoformat(),
            'chain_of_trust': [],
            'records': {
                'dnskey': [],
                'ds': [],
                'rrsig': []
            },
            'errors': []
        }
        
        # IANA root trust anchors (simplified - in production, fetch from IANA)
        self.root_trust_anchors = {
            20326: {
                'key': 'AwEAAaz/tAm8yTn4Mfeh5eyI96WSVexTBAvkMgJzkKTO...',
                'algorithm': 8,
                'flags': 257
            }
        }
    
    def validate(self):
        """Main validation method"""
        try:
            # Step 1: Validate from root down to domain
            chain_valid = self._validate_chain_of_trust()
            
            if chain_valid:
                self.results['status'] = 'valid'
            else:
                # Status was already set in _validate_chain_of_trust
                # Can be 'invalid' (broken DNSSEC) or 'insecure' (no DNSSEC)
                if self.results['status'] == 'unknown':
                    self.results['status'] = 'invalid'
                
        except Exception as e:
            self.results['status'] = 'error'
            self.results['errors'].append(str(e))
            
        return self.results
    
    def _validate_chain_of_trust(self):
        """Validate the complete chain of trust from root to domain"""
        try:
            # Step 1: Check if domain has DNSKEY records
            dnskey_rrset = self._query_dnskey(self.domain_name)
            if not dnskey_rrset:
                self.results['status'] = 'insecure'
                self.results['chain_of_trust'].append({
                    'zone': str(self.domain_name),
                    'status': 'insecure',
                    'error': 'No DNSKEY records found - domain is not signed'
                })
                return False
            
            # Store DNSKEY records
            for rr in dnskey_rrset:
                self.results['records']['dnskey'].append({
                    'zone': str(self.domain_name),
                    'flags': rr.flags,
                    'protocol': rr.protocol,
                    'algorithm': rr.algorithm,
                    'key_tag': dns.dnssec.key_id(rr)
                })
            
            # Step 2: Critical - Check for DS records in parent zone
            # This establishes the chain of trust from parent to child
            ds_rrset = self._query_ds(self.domain_name, None)
            
            if not ds_rrset:
                # Domain has DNSKEY but no DS record in parent - this is the bug!
                self.results['status'] = 'invalid'
                self.results['chain_of_trust'].append({
                    'zone': str(self.domain_name),
                    'status': 'invalid',
                    'error': 'Domain is signed but has no DS record in parent zone - chain of trust broken'
                })
                return False
            
            # Store DS records
            for rr in ds_rrset:
                self.results['records']['ds'].append({
                    'zone': str(self.domain_name),
                    'key_tag': rr.key_tag,
                    'algorithm': rr.algorithm,
                    'digest_type': rr.digest_type,
                    'digest': rr.digest.hex()
                })
            
            # Step 3: Verify DS record matches DNSKEY (simplified check)
            ds_key_tags = {rr.key_tag for rr in ds_rrset}
            dnskey_tags = {dns.dnssec.key_id(rr) for rr in dnskey_rrset}
            
            if not ds_key_tags.intersection(dnskey_tags):
                self.results['status'] = 'invalid'
                self.results['chain_of_trust'].append({
                    'zone': str(self.domain_name),
                    'status': 'invalid',
                    'error': 'DS records do not match any DNSKEY records'
                })
                return False
            
            # If we get here, domain has both DNSKEY and matching DS records
            self.results['chain_of_trust'].append({
                'zone': str(self.domain_name),
                'status': 'valid',
                'algorithm': dnskey_rrset[0].algorithm if dnskey_rrset else None,
                'key_tag': dns.dnssec.key_id(dnskey_rrset[0]) if dnskey_rrset else None
            })
            
            return True
                
        except Exception as e:
            self.results['errors'].append(f"Chain validation error: {str(e)}")
            return False
    
    def _validate_zone(self, zone, parent_zone):
        """Validate a specific zone in the chain"""
        try:
            # Get DNSKEY records for the zone
            dnskey_rrset = self._query_dnskey(zone)
            if not dnskey_rrset:
                self.results['errors'].append(f"No DNSKEY records found for {zone}")
                return False
            
            # Store DNSKEY records
            for rr in dnskey_rrset:
                self.results['records']['dnskey'].append({
                    'zone': str(zone),
                    'flags': rr.flags,
                    'protocol': rr.protocol,
                    'algorithm': rr.algorithm,
                    'key_tag': dns.dnssec.key_id(rr)
                })
            
            # If this is not the root zone, validate DS records from parent
            if parent_zone is not None:
                ds_rrset = self._query_ds(zone, parent_zone)
                if ds_rrset:
                    for rr in ds_rrset:
                        self.results['records']['ds'].append({
                            'zone': str(zone),
                            'key_tag': rr.key_tag,
                            'algorithm': rr.algorithm,
                            'digest_type': rr.digest_type
                        })
            
            # Add to chain of trust
            self.results['chain_of_trust'].append({
                'zone': str(zone),
                'status': 'valid',
                'algorithm': dnskey_rrset[0].algorithm if dnskey_rrset else None,
                'key_tag': dns.dnssec.key_id(dnskey_rrset[0]) if dnskey_rrset else None
            })
            
            return True
            
        except Exception as e:
            self.results['errors'].append(f"Error validating zone {zone}: {str(e)}")
            self.results['chain_of_trust'].append({
                'zone': str(zone),
                'status': 'invalid',
                'error': str(e)
            })
            return False
    
    def _query_dnskey(self, zone):
        """Query DNSKEY records for a zone"""
        try:
            resolver = dns.resolver.Resolver()
            resolver.use_edns(0, dns.flags.DO)  # Enable DNSSEC
            
            answer = resolver.resolve(zone, 'DNSKEY')
            return answer.rrset
            
        except Exception as e:
            logging.error(f"Error querying DNSKEY for {zone}: {e}")
            return None
    
    def _query_ds(self, zone, parent_zone):
        """Query DS records for a zone from its parent"""
        try:
            resolver = dns.resolver.Resolver()
            resolver.use_edns(0, dns.flags.DO)  # Enable DNSSEC
            
            # Query the parent zone for DS records of the child
            answer = resolver.resolve(zone, 'DS')
            return answer.rrset
            
        except Exception as e:
            logging.error(f"Error querying DS for {zone} from {parent_zone}: {e}")
            return None
    
    def _query_rrsig(self, zone, record_type):
        """Query RRSIG records for a specific record type"""
        try:
            resolver = dns.resolver.Resolver()
            resolver.use_edns(0, dns.flags.DO)  # Enable DNSSEC
            
            # Create a DNS query message
            query = dns.message.make_query(zone, record_type, want_dnssec=True)
            
            # Send query to an authoritative server
            response = dns.query.udp(query, '8.8.8.8')  # Using Google DNS
            
            # Extract RRSIG records from the response
            rrsig_records = []
            for rrset in response.answer:
                if rrset.rdtype == dns.rdatatype.RRSIG:
                    for rr in rrset:
                        rrsig_records.append({
                            'type_covered': dns.rdatatype.to_text(rr.type_covered),
                            'algorithm': rr.algorithm,
                            'labels': rr.labels,
                            'original_ttl': rr.original_ttl,
                            'expiration': rr.expiration,
                            'inception': rr.inception,
                            'key_tag': rr.key_tag,
                            'signer': str(rr.signer)
                        })
            
            self.results['records']['rrsig'].extend(rrsig_records)
            return rrsig_records
            
        except Exception as e:
            logging.error(f"Error querying RRSIG for {zone}: {e}")
            return []
    
    def validate_detailed(self):
        """Perform detailed DNSSEC analysis with comprehensive information"""
        # Start with basic validation
        basic_result = self.validate()
        
        # Enhance with detailed information
        detailed_result = {
            **basic_result,
            'detailed_analysis': {
                'raw_dns_queries': [],
                'algorithm_analysis': {},
                'signature_validity': {},
                'key_analysis': {},
                'troubleshooting': [],
                'recommendations': [],
                'query_timing': {}
            }
        }
        
        try:
            # Perform detailed queries with timing
            self._perform_detailed_queries(detailed_result)
            
            # Analyze algorithms and key strength
            self._analyze_algorithms(detailed_result)
            
            # Analyze signature validity
            self._analyze_signatures(detailed_result)
            
            # Analyze key strength
            self._analyze_key_strength(detailed_result)
            
            # Generate troubleshooting suggestions
            self._generate_troubleshooting(detailed_result)
            
            # Generate recommendations
            self._generate_recommendations(detailed_result)
            
        except Exception as e:
            detailed_result['detailed_analysis']['errors'] = [f"Detailed analysis error: {str(e)}"]
            
        return detailed_result
    
    def _perform_detailed_queries(self, result):
        """Perform detailed DNS queries and capture raw responses"""
        queries = [
            ('DNSKEY', self.domain_name),
            ('DS', self.domain_name),
            ('A', self.domain_name),  # To get RRSIG for A records
            ('SOA', self.domain_name)  # To get RRSIG for SOA
        ]
        
        for query_type, zone in queries:
            start_time = time.time()
            try:
                raw_response = self._perform_raw_query(zone, query_type)
                end_time = time.time()
                
                result['detailed_analysis']['raw_dns_queries'].append({
                    'type': query_type,
                    'zone': str(zone),
                    'response': raw_response,
                    'response_time_ms': round((end_time - start_time) * 1000, 2)
                })
                
                result['detailed_analysis']['query_timing'][f"{query_type}_{zone}"] = round((end_time - start_time) * 1000, 2)
                
                # Collect RRSIG records for detailed analysis
                if query_type in ['A', 'SOA']:
                    self._query_rrsig(zone, query_type)
                
            except Exception as e:
                result['detailed_analysis']['raw_dns_queries'].append({
                    'type': query_type,
                    'zone': str(zone),
                    'error': str(e),
                    'response_time_ms': round((time.time() - start_time) * 1000, 2)
                })
    
    def _perform_raw_query(self, zone, query_type):
        """Perform raw DNS query and return formatted dig-style output"""
        try:
            query = dns.message.make_query(zone, query_type, want_dnssec=True)
            response = dns.query.udp(query, '8.8.8.8')
            
            # Format as dig-style output
            output = []
            output.append(f"; DiG 9.x.x +dnssec {query_type} {zone}")
            output.append(f"; {len(response.answer)} answer(s), {len(response.authority)} authority, {len(response.additional)} additional")
            output.append("")
            
            if response.answer:
                output.append(";; ANSWER SECTION:")
                for rrset in response.answer:
                    for rr in rrset:
                        output.append(f"{rrset.name}\t{rrset.ttl}\tIN\t{dns.rdatatype.to_text(rrset.rdtype)}\t{rr}")
                output.append("")
            
            if response.authority:
                output.append(";; AUTHORITY SECTION:")
                for rrset in response.authority:
                    for rr in rrset:
                        output.append(f"{rrset.name}\t{rrset.ttl}\tIN\t{dns.rdatatype.to_text(rrset.rdtype)}\t{rr}")
                output.append("")
            
            if response.additional:
                output.append(";; ADDITIONAL SECTION:")
                for rrset in response.additional:
                    for rr in rrset:
                        output.append(f"{rrset.name}\t{rrset.ttl}\tIN\t{dns.rdatatype.to_text(rrset.rdtype)}\t{rr}")
            
            return "\n".join(output)
            
        except Exception as e:
            return f"Query failed: {str(e)}"
    
    def _analyze_algorithms(self, result):
        """Analyze cryptographic algorithms used"""
        algorithm_info = {
            1: {'name': 'RSA/MD5', 'strength': 'weak', 'recommended': False, 'note': 'Deprecated due to MD5 vulnerabilities'},
            3: {'name': 'DSA/SHA-1', 'strength': 'weak', 'recommended': False, 'note': 'Deprecated due to SHA-1 vulnerabilities'},
            5: {'name': 'RSA/SHA-1', 'strength': 'weak', 'recommended': False, 'note': 'Deprecated due to SHA-1 vulnerabilities'},
            7: {'name': 'RSA/SHA-1 (NSEC3)', 'strength': 'weak', 'recommended': False, 'note': 'Deprecated due to SHA-1 vulnerabilities'},
            8: {'name': 'RSA/SHA-256', 'strength': 'good', 'recommended': True, 'note': 'Widely supported and secure'},
            10: {'name': 'RSA/SHA-512', 'strength': 'good', 'recommended': True, 'note': 'Highly secure but less common'},
            13: {'name': 'ECDSA P-256/SHA-256', 'strength': 'excellent', 'recommended': True, 'note': 'Modern, efficient elliptic curve cryptography'},
            14: {'name': 'ECDSA P-384/SHA-384', 'strength': 'excellent', 'recommended': True, 'note': 'High security elliptic curve cryptography'},
            15: {'name': 'Ed25519', 'strength': 'excellent', 'recommended': True, 'note': 'State-of-the-art EdDSA signature algorithm'},
            16: {'name': 'Ed448', 'strength': 'excellent', 'recommended': True, 'note': 'High-security EdDSA signature algorithm'}
        }
        
        algorithms_found = set()
        for record in result['records']['dnskey']:
            algorithms_found.add(record['algorithm'])
        
        for record in result['records']['ds']:
            algorithms_found.add(record['algorithm'])
        
        analysis = {}
        for alg_id in algorithms_found:
            if alg_id in algorithm_info:
                analysis[alg_id] = algorithm_info[alg_id]
            else:
                analysis[alg_id] = {
                    'name': f'Unknown Algorithm {alg_id}',
                    'strength': 'unknown',
                    'recommended': False,
                    'note': 'Algorithm not recognized'
                }
        
        result['detailed_analysis']['algorithm_analysis'] = analysis
    
    def _analyze_signatures(self, result):
        """Analyze RRSIG signature validity periods"""
        current_time = int(time.time())
        signature_analysis = {
            'current_timestamp': current_time,
            'signatures': [],
            'warnings': []
        }
        
        for rrsig in result['records']['rrsig']:
            sig_info = {
                'type_covered': rrsig['type_covered'],
                'key_tag': rrsig['key_tag'],
                'inception': rrsig['inception'],
                'expiration': rrsig['expiration'],
                'inception_date': datetime.fromtimestamp(rrsig['inception'], tz=timezone.utc).isoformat(),
                'expiration_date': datetime.fromtimestamp(rrsig['expiration'], tz=timezone.utc).isoformat(),
                'valid': rrsig['inception'] <= current_time <= rrsig['expiration'],
                'time_until_expiration': rrsig['expiration'] - current_time
            }
            
            # Check for warnings
            if sig_info['time_until_expiration'] < 86400 * 7:  # Less than 7 days
                signature_analysis['warnings'].append(f"RRSIG for {sig_info['type_covered']} expires soon: {sig_info['expiration_date']}")
            elif sig_info['time_until_expiration'] < 0:
                signature_analysis['warnings'].append(f"RRSIG for {sig_info['type_covered']} has expired: {sig_info['expiration_date']}")
            
            signature_analysis['signatures'].append(sig_info)
        
        result['detailed_analysis']['signature_validity'] = signature_analysis
    
    def _analyze_key_strength(self, result):
        """Analyze DNSSEC key strength and properties"""
        key_analysis = {
            'keys': [],
            'recommendations': []
        }
        
        for dnskey in result['records']['dnskey']:
            key_info = {
                'key_tag': dnskey['key_tag'],
                'algorithm': dnskey['algorithm'],
                'flags': dnskey['flags'],
                'key_type': 'KSK' if dnskey['flags'] & 1 else 'ZSK',  # Key Signing Key vs Zone Signing Key
                'sep_flag': bool(dnskey['flags'] & 1)  # Secure Entry Point
            }
            
            # Algorithm-specific analysis
            if dnskey['algorithm'] in [8, 10]:  # RSA
                key_info['algorithm_family'] = 'RSA'
                # Note: Key size analysis would require parsing the actual key data
                key_analysis['recommendations'].append(f"RSA key {dnskey['key_tag']}: Ensure key size >= 2048 bits for security")
            elif dnskey['algorithm'] in [13, 14]:  # ECDSA
                key_info['algorithm_family'] = 'ECDSA'
                key_analysis['recommendations'].append(f"ECDSA key {dnskey['key_tag']}: Modern elliptic curve algorithm, good choice")
            elif dnskey['algorithm'] in [15, 16]:  # EdDSA
                key_info['algorithm_family'] = 'EdDSA'
                key_analysis['recommendations'].append(f"EdDSA key {dnskey['key_tag']}: State-of-the-art algorithm, excellent choice")
            
            key_analysis['keys'].append(key_info)
        
        result['detailed_analysis']['key_analysis'] = key_analysis
    
    def _generate_troubleshooting(self, result):
        """Generate troubleshooting suggestions based on validation results"""
        troubleshooting = []
        
        if result['status'] == 'invalid':
            # Check for common issues
            has_dnskey = len(result['records']['dnskey']) > 0
            has_ds = len(result['records']['ds']) > 0
            
            if has_dnskey and not has_ds:
                troubleshooting.extend([
                    "🔍 Issue: Domain has DNSKEY records but no DS record in parent zone",
                    "💡 Solution: Contact your domain registrar to publish DS records",
                    "📋 Required DS record parameters:"
                ])
                
                for dnskey in result['records']['dnskey']:
                    if dnskey['flags'] & 1:  # KSK
                        troubleshooting.append(f"   - Key Tag: {dnskey['key_tag']}, Algorithm: {dnskey['algorithm']}")
                        # Calculate expected DS digest (simplified)
                        troubleshooting.append(f"   - Expected DS digest type: 2 (SHA-256)")
            
            elif not has_dnskey:
                troubleshooting.extend([
                    "🔍 Issue: No DNSKEY records found",
                    "💡 Solution: Configure DNSSEC signing on your authoritative name servers",
                    "📋 Steps: Generate KSK/ZSK keys, sign zone, publish DS record"
                ])
            
            elif has_dnskey and has_ds:
                # Key mismatch
                ds_tags = {ds['key_tag'] for ds in result['records']['ds']}
                dnskey_tags = {key['key_tag'] for key in result['records']['dnskey']}
                
                if not ds_tags.intersection(dnskey_tags):
                    troubleshooting.extend([
                        "🔍 Issue: DS and DNSKEY records don't match",
                        "💡 Solution: Ensure DS record matches current DNSKEY",
                        f"📋 Current DNSKEY tags: {', '.join(map(str, dnskey_tags))}",
                        f"📋 Current DS tags: {', '.join(map(str, ds_tags))}"
                    ])
        
        elif result['status'] == 'insecure':
            troubleshooting.extend([
                "🔍 Issue: Domain is not DNSSEC-signed",
                "💡 Solution: Implement DNSSEC signing",
                "📋 Steps:",
                "   1. Generate DNSSEC keys (KSK + ZSK)",
                "   2. Sign your DNS zone",
                "   3. Publish DS record with registrar",
                "   4. Configure automatic key rotation"
            ])
        
        result['detailed_analysis']['troubleshooting'] = troubleshooting
    
    def _generate_recommendations(self, result):
        """Generate security and best practice recommendations"""
        recommendations = []
        
        # Algorithm recommendations
        algorithms_used = {key['algorithm'] for key in result['records']['dnskey']}
        
        if any(alg in [1, 3, 5, 7] for alg in algorithms_used):
            recommendations.append("⚠️ Upgrade deprecated algorithms (RSA/MD5, DSA/SHA-1, RSA/SHA-1) to modern alternatives")
        
        if 8 in algorithms_used:  # RSA/SHA-256
            recommendations.append("✅ RSA/SHA-256 is secure but consider ECDSA for better performance")
        
        if any(alg in [13, 14, 15, 16] for alg in algorithms_used):
            recommendations.append("✅ Modern elliptic curve or EdDSA algorithms detected - excellent choice")
        
        # Key rotation recommendations
        if result['records']['rrsig']:
            min_expiration = min(sig['expiration'] for sig in result['records']['rrsig'])
            current_time = int(time.time())
            days_until_expiration = (min_expiration - current_time) // 86400
            
            if days_until_expiration < 30:
                recommendations.append(f"⏰ Signatures expire in {days_until_expiration} days - plan key rotation")
        
        # Security recommendations
        recommendations.extend([
            "🔄 Implement automated key rotation",
            "📊 Monitor DNSSEC validation regularly",
            "🛡️ Use separate KSK and ZSK keys",
            "⚡ Consider ECDSA algorithms for better performance"
        ])
        
        result['detailed_analysis']['recommendations'] = recommendations
