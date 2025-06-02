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
        return "Google Fact Check API key is not set. Please configure it."
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
                return "❌ No fact-checks found for this claim."
            results = []
            for i, claim in enumerate(claims, start=1):
                text = claim.get("text", "No text")
                claimant = claim.get("claimant", "Unknown")
                claim_review = claim.get("claimReview", [{}])[0]
                publisher = claim_review.get("publisher", {}).get("name", "Unknown Publisher")
                title = claim_review.get("title", "No title")
                rating = claim_review.get("textualRating", "No rating")
                url = claim_review.get("url", "No URL")
                result = f"✅ Result {i}:\nClaim: {text}\nClaimant: {claimant}\nRating: {rating}\nReviewed by: {publisher}\nTitle: {title}\nMore info: {url}\n{'-'*60}"
                results.append(result)
            return "\n".join(results)
        else:
            return f"❌ Error: {response.status_code}\n{response.text}"
    except Exception as e:
        return f"Error contacting Google Fact Check API: {str(e)}"
    # Fallback to model if API fails (optional)
    # result = fake_news_classifier(news_text)[0]
    # label = result['label']
    # score = result['score']
    # if label.upper() == 'REAL':
    #     return f"✅ REAL news with {score * 100:.2f}% confidence."
    # else:
    #     return f"❌ FAKE news with {score * 100:.2f}% confidence."
