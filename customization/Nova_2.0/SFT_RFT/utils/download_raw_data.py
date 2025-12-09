"""
TODO Enter docstring
"""
import requests
from bs4 import BeautifulSoup
import os, time, re


def download_edgar_agreements(num_filings=500, output_path="data/raw/edgar"):
    """Download agreements from multiple SEC forms"""
    
    def clean_html_content(html_text):
        soup = BeautifulSoup(html_text, 'html.parser')
        for tag in soup(['script', 'style', 'meta', 'link', 'nav', 'header', 'footer']):
            tag.decompose()
        clean_text = soup.get_text(separator='\n', strip=True)
        clean_text = re.sub(r'\n\s*\n\s*\n+', '\n\n', clean_text)
        clean_text = re.sub(r' +', ' ', clean_text)
        return clean_text if len(clean_text) > 500 else None
    
    os.makedirs(output_path, exist_ok=True)
    headers = {'User-Agent': 'Research contact@email.com'}
    
    downloaded = 0
    errors = 0
    
    # IMPROVEMENT 1: Multiple form types
    form_types = ['8-K', '10-K', '10-Q', 'S-1', 'S-3', 'DEF 14A', '20-F', 'F-1', '424B', 'D']
    
    
    for form_type in form_types:
        if downloaded >= num_filings:
            break
            
        url = f"https://www.sec.gov/cgi-bin/current?q1=0&q2=1&q3={form_type}"
        
        try:
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code != 200:
                continue
                
            soup = BeautifulSoup(response.text, 'html.parser')
            links = [l['href'] for l in soup.find_all('a', href=True) 
                     if '/Archives/edgar/' in l['href']][:200]
            
            print(f"  {form_type}: Found {len(links)} filings to check")
            
            for path in links:
                if downloaded >= num_filings:
                    break
                    
                try:
                    filing_url = f"https://www.sec.gov{path}"
                    filing_resp = requests.get(filing_url, headers=headers, timeout=10)
                    filing_soup = BeautifulSoup(filing_resp.text, 'html.parser')
                    table = filing_soup.find('table', class_='tableFile')
                    
                    if table:
                        for row in table.find_all('tr'):
                            cells = row.find_all('td')
                            if len(cells) >= 4:
                                desc = cells[3].text.strip()
                                if any(ex in desc for ex in ['EX-10', 'EX-4.', 'AGREEMENT', 'CONTRACT']):
                                    link = cells[2].find('a')
                                    if link:
                                        doc_url = f"https://www.sec.gov{link['href']}"
                                        doc_resp = requests.get(doc_url, headers=headers, timeout=10)
                                        
                                        if doc_resp.status_code == 200:
                                            clean_text = clean_html_content(doc_resp.text)
                                            if clean_text:
                                                filename = f"{output_path}/agreement_{downloaded:03d}.txt"
                                                with open(filename, 'w', encoding='utf-8') as f:
                                                    f.write(clean_text)
                                                downloaded += 1
                                                if downloaded % 20 == 0:
                                                    print(f"    Downloaded: {downloaded}")
                                                break
                    
                    time.sleep(0.11)  # SEC rate limit compliance
                    
                except Exception:
                    errors += 1
                    continue
                    
        except Exception:
            errors += 1
            continue
    
    print(f"✓ EDGAR: {downloaded} agreements from {len(form_types)} form types, {errors} errors")

def download_sec_regulations(output_path="data/raw/regulations"):    
    os.makedirs(output_path, exist_ok=True)
    
    # IMPROVEMENT: Expanded regulation list
    regs = {
        # Regulation D (Private Placements)
        "rule_506": "230.506", "rule_505": "230.505", "rule_504": "230.504",
        "rule_503": "230.503", "rule_502": "230.502", "rule_501": "230.501",
        # Rule 144 (Resale of Restricted Securities)
        "rule_144": "230.144", "rule_144A": "230.144A", 
        # Other 230 Rules
        "rule_405": "230.405", "rule_163": "230.163", "rule_152": "230.152", 
        "rule_215": "230.215", "rule_134": "230.134", "rule_135": "230.135",
        "rule_147": "230.147", "rule_147A": "230.147A",
        # Regulation A
        "reg_A_251": "230.251", "reg_A_252": "230.252", "reg_A_253": "230.253",
        # Regulation S
        "reg_S_901": "230.901", "reg_S_903": "230.903", "reg_S_902": "230.902",
        # Rule 10b-5 and related
        "rule_10b5": "240.10b-5", "rule_10b5-1": "240.10b5-1", "rule_10b5-2": "240.10b5-2",
        # Form Requirements
        "form_S1": "239.11", "form_S3": "239.13", "form_F1": "239.31",
        # Additional Rules
        "rule_701": "230.701", "rule_901": "230.901",
        "rule_14a-8": "240.14a-8",    # Shareholder proposals  
        "rule_14a-9": "240.14a-9",    # False proxy statements
        "rule_415": "230.415",        # Shelf registration procedures
        "rule_424": "230.424",        # Filing of prospectuses
        "rule_904": "230.904",        # Reg S safe harbor conditions  
        "rule_16a-1": "240.16a-1",    # Insider reporting
        "rule_13d-1": "240.13d-1",    # Beneficial ownership reporting
        "regulation_FD": "243.100"    # Fair disclosure regulation
    }
    
    downloaded = 0
    errors = 0
    
    for name, cfr_id in regs.items():
        url = f"https://www.law.cornell.edu/cfr/text/17/{cfr_id}"
        
        try:
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                content_div = soup.find('div', {'id': 'content'})
                
                if content_div:
                    for tag in content_div(['script', 'style', 'nav', 'aside', 'header', 'footer']):
                        tag.decompose()
                    clean_text = content_div.get_text(separator='\n', strip=True)
                else:
                    for tag in soup(['script', 'style', 'nav', 'aside', 'header', 'footer']):
                        tag.decompose()
                    clean_text = soup.get_text(separator='\n', strip=True)
                
                with open(f"{output_path}/{name}.txt", 'w', encoding='utf-8') as f:
                    f.write(clean_text)
                downloaded += 1
                if downloaded % 10 == 0:
                    print(f"  Regulations: {downloaded}")
            
            time.sleep(0.2)
            
        except Exception:
            errors += 1
            continue
    
    print(f"✓ Regulations: {downloaded} rules, {errors} errors")

def download_courtlistener_cases(api_key, output_path="data/raw/cases", max_cases=500):
    """Download expanded set of securities cases"""
    
    if not api_key: raise ValueError("api_key is required for CourtListener API access")

    os.makedirs(output_path, exist_ok=True)
    headers = {"Authorization": f"Token {api_key}"}
    
    queries = [
        # Rule 506
        "Rule 506 accredited investor", "Rule 506 general solicitation",
        "Rule 506(b) verification", "Rule 506(c) general advertising",
        # Rule 144
        "Rule 144 holding period", "Rule 144 restricted securities",
        "Rule 144A qualified institutional buyer", "Rule 144 volume limitations",
        # Rule 10b-5
        "Rule 10b-5 fraud", "Rule 10b-5 omissions", "Rule 10b-5 materiality",
        # Private Placements
        "private placement exemption", "private offering", "Regulation D exemption",
        # Investor Classification
        "accredited investor", "sophisticated investor", "qualified institutional buyer",
        "accredited investor verification",
        # Securities Act
        "Securities Act Section 5", "registration exemption", 
        "blue sky laws", "state securities laws",
        # Offering Requirements
        "preliminary offering circular", "resale restrictions",
        "lock-up agreement", "integration doctrine",
        # 
        "Regulation A offering exemption",
        "Rule 251 small offering qualification", 
        "Regulation S offshore transaction",
        "Rule 901 safe harbor provision",
        "Form S-1 registration statement liability",
        "Section 11 registration statement",
        "Rule 701 employee compensation plan",
        "proxy statement disclosure Rule 14a",
        "10-K annual report disclosure",
        "beneficial ownership Rule 13d"
    ]
    
    all_cases = []
    errors = 0
    
    for query in queries:
        for page in range(3):  # 3 pages × 20 results = 60 per query
            if len(all_cases) >= max_cases:
                break
                
            url = "https://www.courtlistener.com/api/rest/v3/search/"
            params = {
                "q": query, 
                "type": "o", 
                "order_by": "score desc",
                "page": page + 1
            }
            
            try:
                response = requests.get(url, headers=headers, params=params, timeout=15)
                
                if response.status_code == 200:
                    results = response.json().get('results', [])
                    for case in results[:20]:
                        if len(all_cases) >= max_cases:
                            break
                        case_text = f"Case: {case['caseName']}\nDate: {case['dateFiled']}\nSummary: {case['snippet']}\n"
                        all_cases.append(case_text)
                    
                    if len(all_cases) % 50 == 0:
                        print(f"  Cases: {len(all_cases)}")
                    
                    if not results:  # No more results
                        break
                        
                elif response.status_code == 429:
                    time.sleep(10)
                    break
                else:
                    break
                    
                time.sleep(1.5)  # Rate limit compliance
                
            except Exception:
                errors += 1
                break
    
    if all_cases:
        with open(f"{output_path}/cases.txt", 'w') as f:
            f.write("\n" + "="*80 + "\n".join(all_cases))
        print(f"✓ CourtListener: {len(all_cases)} cases, {errors} errors")
    else:
        print(f"✗ CourtListener: No cases downloaded")
