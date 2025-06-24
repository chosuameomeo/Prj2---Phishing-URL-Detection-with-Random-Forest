from flask import Flask, request, jsonify
import joblib
import pandas as pd
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urlsplit
import re
from tldextract import extract
import traceback

app = Flask(__name__)

# Tải model đã được train
try:
    model = joblib.load('random_forest_model.pkl')
    print("Model loaded successfully!")
except FileNotFoundError:
    print("Model file 'random_forest_model.pkl' not found! A dummy model will be created for testing.")
    from sklearn.ensemble import RandomForestClassifier
    X_dummy = pd.DataFrame([[0]*48 for _ in range(10)]) 
    y_dummy = pd.Series([0,1]*5)
    dummy_model = RandomForestClassifier()
    dummy_model.fit(X_dummy, y_dummy)
    model = dummy_model
    joblib.dump(model, 'random_forest_model.pkl')
    print("Dummy model created, loaded, and saved as 'random_forest_model.pkl'.")

# Danh sách các feature
FEATURE_COLUMNS = [
    'URLLength', 'DomainLength', 'IsDomainIP', 'CharContinuationRate', 'TLDLength',
    'NoOfSubDomain', 'HasObfuscation', 'NoOfObfuscatedChar', 'ObfuscationRatio',
    'NoOfLettersInURL', 'LetterRatioInURL', 'NoOfDegitsInURL', 'DegitRatioInURL',
    'NoOfEqualsInURL', 'NoOfQMarkInURL', 'NoOfAmpersandInURL',
    'NoOfOtherSpecialCharsInURL', 'SpacialCharRatioInURL', 'IsHTTPS',
    'LineOfCode', 'LargestLineLength', 'HasTitle', 'DomainTitleMatchScore',
    'URLTitleMatchScore', 'HasFavicon', 'Robots', 'IsResponsive',
    'NoOfURLRedirect', 'NoOfSelfRedirect', 'HasDescription', 'NoOfPopup',
    'NoOfiFrame', 'HasExternalFormSubmit', 'HasSocialNet', 'HasSubmitButton',
    'HasHiddenFields', 'HasPasswordField', 'Bank', 'Pay', 'Crypto',
    'HasCopyrightInfo', 'NoOfImage', 'NoOfCSS', 'NoOfJS', 'NoOfSelfRef',
    'NoOfEmptyRef', 'NoOfExternalRef'
]

def extract_features(url):
    features = {}
    
    # 1. Phân tích URL 
    parsed_url = urlparse(url)
    domain_info = extract(url)
    domain = domain_info.domain + '.' + domain_info.suffix

    features['URLLength'] = len(url)
    features['DomainLength'] = len(domain)

    ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    features['IsDomainIP'] = 1 if re.match(ip_pattern, parsed_url.netloc) else 0

    longest_consecutive_letters = max(len(s) for s in re.findall(r'[a-zA-Z]+', url)) if re.search(r'[a-zA-Z]+', url) else 0
    features['CharContinuationRate'] = longest_consecutive_letters / features['URLLength'] if features['URLLength'] > 0 else 0

    features['TLDLength'] = len(domain_info.suffix)
    features['NoOfSubDomain'] = len(domain_info.subdomain.split('.')) if domain_info.subdomain else 0

    obfuscated_chars = re.findall(r'%[0-9a-fA-F]{2}', url)
    features['HasObfuscation'] = 1 if obfuscated_chars else 0
    features['NoOfObfuscatedChar'] = len(obfuscated_chars)
    features['ObfuscationRatio'] = features['NoOfObfuscatedChar'] / features['URLLength'] if features['URLLength'] > 0 else 0

    features['NoOfLettersInURL'] = len(re.findall(r'[a-zA-Z]', url))
    features['LetterRatioInURL'] = features['NoOfLettersInURL'] / features['URLLength'] if features['URLLength'] > 0 else 0
    features['NoOfDegitsInURL'] = len(re.findall(r'[0-9]', url))
    features['DegitRatioInURL'] = features['NoOfDegitsInURL'] / features['URLLength'] if features['URLLength'] > 0 else 0
    features['NoOfEqualsInURL'] = url.count('=')
    features['NoOfQMarkInURL'] = url.count('?')
    features['NoOfAmpersandInURL'] = url.count('&')
    
    other_specials = re.findall(r'[-_@!$*+]', url)
    features['NoOfOtherSpecialCharsInURL'] = len(other_specials)

    all_specials = features['NoOfEqualsInURL'] + features['NoOfQMarkInURL'] + features['NoOfAmpersandInURL'] + features['NoOfOtherSpecialCharsInURL']
    features['SpacialCharRatioInURL'] = all_specials / features['URLLength'] if features['URLLength'] > 0 else 0

    features['IsHTTPS'] = 1 if parsed_url.scheme == 'https' else 0

    # 2. Phân tích nội dung trang
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=5, allow_redirects=True)
        soup = BeautifulSoup(response.content, 'html.parser', from_encoding=response.encoding)
        html_content = str(soup)

        features['LineOfCode'] = len(html_content.splitlines())
        features['LargestLineLength'] = max(len(line) for line in html_content.splitlines()) if features['LineOfCode'] > 0 else 0
        
        title_tag = soup.find('title')
        features['HasTitle'] = 1 if title_tag and title_tag.string else 0
        title_text = title_tag.string.strip() if features['HasTitle'] else ''
        
        domain_words = set(re.findall(r'\w+', domain.lower()))
        title_words = set(re.findall(r'\w+', title_text.lower()))
        url_words = set(re.findall(r'\w+', url.lower()))
        features['DomainTitleMatchScore'] = len(domain_words.intersection(title_words)) / len(domain_words.union(title_words)) if domain_words.union(title_words) else 0
        features['URLTitleMatchScore'] = len(url_words.intersection(title_words)) / len(url_words.union(title_words)) if url_words.union(title_words) else 0

        features['HasFavicon'] = 1 if soup.find('link', rel=re.compile(r'icon', re.I)) else 0
        
        try:
            robots_resp = requests.get(urlparse(url).scheme + '://' + parsed_url.netloc + '/robots.txt', timeout=2)
            features['Robots'] = 1 if robots_resp.status_code == 200 and 'Disallow: /' in robots_resp.text else 0
        except:
            features['Robots'] = 0

        features['IsResponsive'] = 1 if soup.find('meta', attrs={'name': 'viewport'}) else 0
        features['NoOfURLRedirect'] = len(response.history)
        self_redirects = [r for r in response.history if urlparse(r.url).netloc == parsed_url.netloc]
        features['NoOfSelfRedirect'] = len(self_redirects)
        features['HasDescription'] = 1 if soup.find('meta', attrs={'name': 'description'}) else 0
        
        scripts = soup.find_all('script')
        popup_count = 0
        for script in scripts:
            if script.string:
                popup_count += script.string.lower().count('window.open')
        features['NoOfPopup'] = popup_count

        features['NoOfiFrame'] = len(soup.find_all('iframe'))
        
        forms = soup.find_all('form')
        features['HasExternalFormSubmit'] = 0
        for form in forms:
            action = form.get('action', '').strip()
            if action and not action.startswith('#') and urlparse(action).netloc not in ['', parsed_url.netloc]:
                features['HasExternalFormSubmit'] = 1
                break
        
        features['HasSocialNet'] = 1 if soup.find('a', href=re.compile(r'facebook\.com|twitter\.com|instagram\.com')) else 0
        features['HasSubmitButton'] = 1 if soup.find('input', {'type': 'submit'}) or soup.find('button', {'type': 'submit'}) else 0
        features['HasHiddenFields'] = 1 if soup.find('input', {'type': 'hidden'}) else 0
        features['HasPasswordField'] = 1 if soup.find('input', {'type': 'password'}) else 0

        page_text = soup.get_text().lower()
        features['Bank'] = 1 if any(word in page_text for word in ['bank', 'ngân hàng']) else 0
        features['Pay'] = 1 if any(word in page_text for word in ['pay', 'payment', 'thanh toán']) else 0
        features['Crypto'] = 1 if any(word in page_text for word in ['crypto', 'bitcoin', 'ethereum', 'coin']) else 0
        features['HasCopyrightInfo'] = 1 if 'copyright' in page_text or '©' in page_text else 0

        features['NoOfImage'] = len(soup.find_all('img'))
        features['NoOfCSS'] = len(soup.find_all('link', {'rel': 'stylesheet'}))
        features['NoOfJS'] = len(soup.find_all('script'))

        links = soup.find_all('a', href=True)
        self_ref_count, empty_ref_count, external_ref_count = 0, 0, 0
        for link in links:
            href = link['href']
            if not href or href.startswith('#') or href.startswith('javascript:'):
                empty_ref_count += 1
            elif urlparse(href).netloc == parsed_url.netloc or not urlparse(href).netloc:
                self_ref_count += 1
            else:
                external_ref_count += 1
        features['NoOfSelfRef'] = self_ref_count
        features['NoOfEmptyRef'] = empty_ref_count
        features['NoOfExternalRef'] = external_ref_count

    except Exception as e:
        print(f"Could not fetch or parse URL {url}. Error: {e}")
        content_features = [
            'LineOfCode', 'LargestLineLength', 'HasTitle', 'DomainTitleMatchScore', 
            'URLTitleMatchScore', 'HasFavicon', 'Robots', 'IsResponsive', 
            'NoOfURLRedirect', 'NoOfSelfRedirect', 'HasDescription', 'NoOfPopup', 
            'NoOfiFrame', 'HasExternalFormSubmit', 'HasSocialNet', 'HasSubmitButton', 
            'HasHiddenFields', 'HasPasswordField', 'Bank', 'Pay', 'Crypto', 
            'HasCopyrightInfo', 'NoOfImage', 'NoOfCSS', 'NoOfJS', 'NoOfSelfRef', 
            'NoOfEmptyRef', 'NoOfExternalRef'
        ]
        for f in content_features:
            if f not in features:
                features[f] = 0

    for col in FEATURE_COLUMNS:
        if col not in features:
            features[col] = 0
            
    return pd.DataFrame([features])[FEATURE_COLUMNS]

# Kiểm tra URL
@app.route('/check_url', methods=['POST'])
def check_url():
    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({'error': 'URL not provided'}), 400

    url_to_check = data['url']
    
    try:
        feature_vector = extract_features(url_to_check)
        prediction = model.predict(feature_vector)
        probability = model.predict_proba(feature_vector)
        result = 'phishing' if prediction[0] == 1 else 'safe'
        
        print(f"URL: {url_to_check} -> Prediction: {result} (Phishing Probability: {probability[0][1]:.2f})")

        return jsonify({'status': result, 'probability': float(probability[0][1])})

    except Exception as e:
        print(f"An error occurred during feature extraction or prediction: {e}")
        traceback.print_exc()
        return jsonify({'status': 'safe', 'error': str(e)})

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)  