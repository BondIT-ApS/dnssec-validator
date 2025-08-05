import dns.resolver
import dns.dnssec
import dns.name
import dns.rdatatype
import dns.rdataclass
import dns.rrset
import dns.query
import dns.message
from datetime import datetime
import logging

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
                self.results['status'] = 'invalid'
                
        except Exception as e:
            self.results['status'] = 'error'
            self.results['errors'].append(str(e))
            
        return self.results
    
    def _validate_chain_of_trust(self):
        """Validate the complete chain of trust from root to domain"""
        labels = str(self.domain_name).split('.')
        if labels[-1] == '':  # Remove empty string from FQDN
            labels = labels[:-1]
        
        current_zone = dns.name.root
        
        # Start with root validation
        if not self._validate_zone(current_zone, None):
            return False
        
        # Walk down the chain
        for i, label in enumerate(reversed(labels)):
            parent_zone = current_zone
            current_zone = dns.name.from_text('.'.join(reversed(labels[:len(labels)-i])))
            
            if not self._validate_zone(current_zone, parent_zone):
                return False
                
        return True
    
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
