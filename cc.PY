import requests
import json
from typing import Dict, List, Optional, Any
from datetime import datetime

class DOIValidator:
    """Simple DOI validator that retrieves publication information from CrossRef"""
    
    def __init__(self):
        self.base_url = "https://api.crossref.org/works/"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'DOIValidator/1.0 (https://example.com/contact)'
        })
    
    def validate_doi(self, doi: str) -> Dict[str, Any]:
        """Check if DOI exists and retrieve publication information"""
        # Clean the DOI (remove any URL prefixes)
        doi = doi.strip()
        if doi.startswith('http://dx.doi.org/'):
            doi = doi.replace('http://dx.doi.org/', '')
        elif doi.startswith('https://doi.org/'):
            doi = doi.replace('https://doi.org/', '')
        elif doi.startswith('doi:'):
            doi = doi.replace('doi:', '')
        
        # Make API request
        url = f"{self.base_url}{doi}"
        
        try:
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                publication = data.get('message', {})
                
                # Extract and format the information
                result = {
                    'doi': doi,
                    'exists': True,
                    'type': publication.get('type', 'unknown'),
                    'title': self._extract_title(publication),
                    'authors': self._extract_authors(publication),
                    'published_date': self._extract_date(publication),
                    'journal': self._extract_journal(publication),
                    'publisher': publication.get('publisher', ''),
                    'volume': publication.get('volume', ''),
                    'issue': publication.get('issue', ''),
                    'pages': publication.get('page', ''),
                    'url': f"https://doi.org/{doi}",
                    'citations_count': publication.get('is-referenced-by-count', 0),
                    'abstract': publication.get('abstract', ''),
                    'subject': publication.get('subject', [])
                }
                
                return result
                
            elif response.status_code == 404:
                return {
                    'doi': doi,
                    'exists': False,
                    'error': 'DOI not found in CrossRef database'
                }
            else:
                return {
                    'doi': doi,
                    'exists': False,
                    'error': f'API error: {response.status_code}'
                }
                
        except requests.exceptions.Timeout:
            return {
                'doi': doi,
                'exists': False,
                'error': 'Request timed out'
            }
        except Exception as e:
            return {
                'doi': doi,
                'exists': False,
                'error': f'Error: {str(e)}'
            }
    
    def _extract_title(self, publication: Dict) -> str:
        """Extract title from publication data"""
        title = publication.get('title', [])
        if isinstance(title, list) and title:
            return title[0]
        elif isinstance(title, str):
            return title
        return 'No title available'
    
    def _extract_authors(self, publication: Dict) -> List[Dict[str, str]]:
        """Extract and format author information"""
        authors = []
        author_list = publication.get('author', [])
        
        for author in author_list:
            author_info = {
                'given_name': author.get('given', ''),
                'family_name': author.get('family', ''),
                'full_name': f"{author.get('given', '')} {author.get('family', '')}".strip(),
                'orcid': author.get('ORCID', ''),
                'affiliation': []
            }
            
            # Extract affiliations
            for affiliation in author.get('affiliation', []):
                if isinstance(affiliation, dict):
                    author_info['affiliation'].append(affiliation.get('name', ''))
            
            authors.append(author_info)
        
        return authors
    
    def _extract_date(self, publication: Dict) -> Dict[str, Any]:
        """Extract publication date information"""
        date_info = {}
        
        # Try different date fields
        for date_type in ['published-print', 'published-online', 'published', 'created']:
            if date_type in publication:
                date_parts = publication[date_type].get('date-parts', [[]])
                if date_parts and date_parts[0]:
                    parts = date_parts[0]
                    date_info = {
                        'year': parts[0] if len(parts) > 0 else None,
                        'month': parts[1] if len(parts) > 1 else None,
                        'day': parts[2] if len(parts) > 2 else None,
                        'type': date_type
                    }
                    break
        
        # Format date string
        if date_info.get('year'):
            date_str = str(date_info['year'])
            if date_info.get('month'):
                date_str = f"{date_info['year']}-{date_info['month']:02d}"
                if date_info.get('day'):
                    date_str = f"{date_info['year']}-{date_info['month']:02d}-{date_info['day']:02d}"
            date_info['formatted'] = date_str
        else:
            date_info['formatted'] = 'Date not available'
        
        return date_info
    
    def _extract_journal(self, publication: Dict) -> str:
        """Extract journal/container title"""
        container = publication.get('container-title', [])
        if isinstance(container, list) and container:
            return container[0]
        elif isinstance(container, str):
            return container
        return ''
    
    def format_citation(self, result: Dict) -> str:
        """Format the result as a citation"""
        if not result['exists']:
            return f"DOI {result['doi']} not found"
        
        # Build citation string
        authors = result['authors']
        if len(authors) > 3:
            author_str = f"{authors[0]['family_name']}, {authors[0]['given_name'][0]}. et al."
        else:
            author_parts = []
            for author in authors:
                if author['family_name'] and author['given_name']:
                    author_parts.append(f"{author['family_name']}, {author['given_name'][0]}.")
                elif author['family_name']:
                    author_parts.append(author['family_name'])
            author_str = ", ".join(author_parts)
        
        year = result['published_date'].get('year', 'n.d.')
        title = result['title']
        journal = result['journal']
        volume = result['volume']
        pages = result['pages']
        
        # Format based on type
        if result['type'] == 'journal-article':
            citation = f"{author_str} ({year}). {title}. {journal}"
            if volume:
                citation += f", {volume}"
            if pages:
                citation += f", {pages}"
            citation += f". https://doi.org/{result['doi']}"
        else:
            # Generic format for other types
            citation = f"{author_str} ({year}). {title}."
            if journal:
                citation += f" {journal}."
            citation += f" https://doi.org/{result['doi']}"
        
        return citation


def main():
    """Example usage of the DOI validator"""
    
    # Test DOIs - mix of real and fake
    test_dois = [
        # Real DOIs
        "10.1038/s41592-021-01264-7",  # Your professor's Nature Methods paper
        "10.1038/nature14539",          # LeCun's Deep Learning paper
        "10.48550/arXiv.1706.03762",    # Attention is All You Need (arXiv)
        
        # Fake DOIs
        "10.1234/fake-doi-12345",
        "10.9999/this-does-not-exist",
        "not-even-a-valid-doi-format"
    ]
    
    validator = DOIValidator()
    
    print("DOI VALIDATOR")
    print("=" * 80)
    print()
    
    for i, doi in enumerate(test_dois, 1):
        print(f"[{i}] Checking DOI: {doi}")
        print("-" * 80)
        
        result = validator.validate_doi(doi)
        
        if result['exists']:
            print(f"✓ FOUND: {result['type'].replace('-', ' ').title()}")
            print(f"  Title: {result['title']}")
            print(f"  Authors: {', '.join([a['full_name'] for a in result['authors'][:3]])}"
                  f"{' et al.' if len(result['authors']) > 3 else ''}")
            print(f"  Published: {result['published_date']['formatted']}")
            print(f"  Journal/Venue: {result['journal']}")
            if result['volume']:
                print(f"  Volume: {result['volume']}, Issue: {result['issue']}, Pages: {result['pages']}")
            print(f"  Publisher: {result['publisher']}")
            print(f"  Citations: {result['citations_count']}")
            print(f"  URL: {result['url']}")
            print()
            print("  Formatted citation:")
            print(f"  {validator.format_citation(result)}")
        else:
            print(f"✗ NOT FOUND: {result['error']}")
        
        print()
    
    # Interactive mode
    print("\n" + "=" * 80)
    print("INTERACTIVE MODE - Enter DOIs to validate (or 'quit' to exit)")
    print("=" * 80)
    
    while True:
        doi = input("\nEnter DOI: ").strip()
        if doi.lower() in ['quit', 'exit', 'q']:
            break
        
        if doi:
            result = validator.validate_doi(doi)
            
            if result['exists']:
                print(f"\n✓ FOUND!")
                print(f"Title: {result['title']}")
                print(f"Authors: {', '.join([a['full_name'] for a in result['authors'][:3]])}"
                      f"{' et al.' if len(result['authors']) > 3 else ''}")
                print(f"Year: {result['published_date'].get('year', 'N/A')}")
                print(f"Type: {result['type']}")
                print(f"\nFormatted citation:")
                print(validator.format_citation(result))
            else:
                print(f"\n✗ NOT FOUND: {result['error']}")
    
    print("\nThank you for using DOI Validator!")


if __name__ == "__main__":
    main()