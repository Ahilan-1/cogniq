from flask import Flask, request, render_template, Markup
import requests
from bs4 import BeautifulSoup
from newspaper import Article
from gensim.summarization import summarize as gensim_summarize
import nltk
from nltk.tokenize import sent_tokenize
from nltk.corpus import stopwords
from nltk.probability import FreqDist

app = Flask(__name__)

nltk.download('punkt', quiet=True)
nltk.download('stopwords', quiet=True)

def google_search(query):
    url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.text

def parse_search_results(html):
    soup = BeautifulSoup(html, 'html.parser')
    results = []
    for g in soup.find_all('div', class_='tF2Cxc'):
        title = g.find('h3')
        title = title.text if title else 'No title found'
        link = g.find('a')['href']
        snippet = g.find('div', class_='VwiC3b')
        snippet = snippet.text if snippet else 'No snippet found'
        results.append({'title': title, 'link': link, 'snippet': snippet})
    return results

def fetch_and_summarize(url):
    try:
        article = Article(url)
        article.download()
        article.parse()
        article.nlp()
        return article.summary
    except:
        return None

def highlight_important_sentences(text, query, num_sentences=3):
    sentences = sent_tokenize(text)
    words = nltk.word_tokenize(text.lower())
    stop_words = set(stopwords.words('english'))
    words = [word for word in words if word.isalnum() and word not in stop_words]
    
    freq_dist = FreqDist(words)
    query_words = set(query.lower().split())
    
    def sentence_importance(sentence):
        sentence_words = set(word.lower() for word in nltk.word_tokenize(sentence) if word.isalnum())
        return sum(freq_dist[word] for word in sentence_words) + sum(5 for word in sentence_words if word in query_words)
    
    ranked_sentences = sorted([(sentence, sentence_importance(sentence)) for sentence in sentences], 
                              key=lambda x: x[1], reverse=True)
    
    highlighted_sentences = set(sentence for sentence, _ in ranked_sentences[:num_sentences])
    
    highlighted_text = []
    for sentence in sentences:
        if sentence in highlighted_sentences:
            highlighted_text.append(f'<mark class="highlight">{sentence}</mark>')
        else:
            highlighted_text.append(sentence)
    
    return ' '.join(highlighted_text)

def combine_summaries(summaries, query):
    combined_text = " ".join(summaries)
    if combined_text:
        try:
            summary = gensim_summarize(combined_text, ratio=0.3)
        except ValueError:
            summary = combined_text[:1000] + "..." if len(combined_text) > 1000 else combined_text
        return highlight_important_sentences(summary, query)
    return "No useful summary available."

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        query = request.form["query"]
        html = google_search(query)
        results = parse_search_results(html)
        summarized_results = []
        all_summaries = []

        for result in results:
            summary = fetch_and_summarize(result['link'])
            if summary:
                highlighted_summary = highlight_important_sentences(summary, query)
                summarized_results.append({
                    'title': result['title'],
                    'link': result['link'],
                    'snippet': result['snippet'],
                    'summary': Markup(highlighted_summary)
                })
                all_summaries.append(summary)

        combined_summary = combine_summaries(all_summaries, query)
        
        return render_template("index.html", 
                               results=summarized_results, 
                               query=query, 
                               combined_summary=Markup(combined_summary))
    
    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)