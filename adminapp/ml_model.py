import os
import requests
from transformers import pipeline

# Load the new RoBERTa-based fake news detection model
fake_news_classifier = pipeline("text-classification", model="winterForestStump/Roberta-fake-news-detector")

# Google Fact Check API endpoint
FACT_CHECK_API_URL = "https://factchecktools.googleapis.com/v1alpha1/claims:search"

# Directly set your API key here for testing (remove in production)
API_KEY = "AIzaSyA1aqMvXRgTfQPda9nZV9ZFJrdAmhrhtzM"

def predict_fake_news(news_text):
    if not API_KEY:
        return [{"error": "Google Fact Check API key is not set. Please configure it."}]
    
    params = {
        "query": news_text,
        "key": API_KEY,
        "languageCode": "en"
    }
    
    try:
        response = requests.get(FACT_CHECK_API_URL, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            claims = data.get("claims", [])
            if not claims:
                return [{"error": "No fact-checks found for this claim."}]
            
            results = []
            for claim in claims:
                result = {
                    "claim": claim.get("text", "No text"),
                    "claimant": claim.get("claimant", "Unknown"),
                    "rating": claim.get("claimReview", [{}])[0].get("textualRating", "No rating"),
                    "reviewer": claim.get("claimReview", [{}])[0].get("publisher", {}).get("name", "Unknown Publisher"),
                    "title": claim.get("claimReview", [{}])[0].get("title", "No title"),
                    "link": claim.get("claimReview", [{}])[0].get("url", "No URL")
                }
                results.append(result)
            return results
        else:
            return [{"error": f"API Error: {response.status_code} - {response.text}"}]
    except Exception as e:
        return [{"error": f"Error contacting Google Fact Check API: {str(e)}"}]
    
    # Fallback to model if API fails (optional, commented out as in original)
    # result = fake_news_classifier(news_text)[0]
    # label = result['label']
    # score = result['score']
    # if label.upper() == 'REAL':
    #     return [{"claim": news_text, "rating": "Real", "score": f"{score * 100:.2f}%"}]
    # else:
    #     return [{"claim": news_text, "rating": "Fake", "score": f"{score * 100:.2f}%"}]