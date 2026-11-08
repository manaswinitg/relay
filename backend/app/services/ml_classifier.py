import os
import re
from typing import Dict, Any, Tuple
import numpy as np

# Sample realistic emergency domain corpus for bootstrap training
TRAINING_DATA = [
    # MEDICAL
    ("Severe chest pain and difficulty breathing after building collapse", "MEDICAL", "CRITICAL"),
    ("Diabetic patient trapped without insulin for two days, unconscious", "MEDICAL", "CRITICAL"),
    ("Elderly woman fell and broke hip, heavy bleeding needs ambulance", "MEDICAL", "CRITICAL"),
    ("Severe lacerations from shattered window glass, need stitches and sterile gauze", "MEDICAL", "HIGH"),
    ("Child running 104 fever, shivering with dehydration", "MEDICAL", "HIGH"),
    ("Need prescription heart medication refills after evacuation", "MEDICAL", "MEDIUM"),
    ("Minor cuts and scrapes from debris, first aid supplies requested", "MEDICAL", "LOW"),

    # WATER
    ("Drinking water completely contaminated with sewage, no clean water for 200 people", "WATER", "CRITICAL"),
    ("Dehydrated infants and mothers, municipal water main ruptured, urgent water needed", "WATER", "HIGH"),
    ("Running out of bottled drinking water at neighborhood shelter, 50 people remaining", "WATER", "HIGH"),
    ("Need potable water purification tablets or water filtration unit", "WATER", "MEDIUM"),
    ("Tap water smells like sulfur, request water tanker dispatch", "WATER", "MEDIUM"),
    ("Low water pressure in building, inquiring about water distribution times", "WATER", "LOW"),

    # FOOD
    ("No food for 3 days, family with three young toddlers starving in attic", "FOOD", "HIGH"),
    ("Community hall kitchen exhausted all canned goods, 150 refugees need meals", "FOOD", "HIGH"),
    ("Requesting dry rations, rice, beans, and baby formula", "FOOD", "MEDIUM"),
    ("Need non-perishable ready-to-eat meals (MREs) for stranded rescue crew", "FOOD", "MEDIUM"),
    ("Looking for food pantry open hours near downtown", "FOOD", "LOW"),

    # SHELTER
    ("Roof ripped off by tornado, 6 people exposed to torrential freezing rain", "SHELTER", "CRITICAL"),
    ("Flood waters rising above first floor ceiling, need immediate boat rescue to dry shelter", "SHELTER", "CRITICAL"),
    ("Apartment basement flooded, displaced family of five needs emergency shelter bed", "SHELTER", "HIGH"),
    ("Need blankets, sleeping bags, and cots for local gymnasium shelter", "SHELTER", "MEDIUM"),
    ("Where is the nearest pet-friendly evacuation shelter?", "SHELTER", "LOW"),

    # HAZARD
    ("Live electrical high-voltage wire downed in flooded street, sparking actively", "HAZARD", "CRITICAL"),
    ("Strong gas smell near collapsed residential duplex, risk of explosion", "HAZARD", "CRITICAL"),
    ("Main bridge approach cracked and submerged, road completely impassable", "HAZARD", "HIGH"),
    ("Large oak tree blocking two-lane emergency route on Elm Street", "HAZARD", "MEDIUM"),
    ("Streetlights non-functional at intersection, minor traffic slowdown", "HAZARD", "LOW"),
]


class EmergencyNLPClassifier:
    """
    Lightweight Emergency NLP Classifier.
    Uses TF-IDF + Multinomial Naive Bayes / Logistic Regression when scikit-learn is available,
    with an intelligent semantic keyword fallback.
    """

    def __init__(self):
        self.is_trained = False
        self.vectorizer = None
        self.category_classifier = None
        self.urgency_classifier = None
        self._bootstrap_model()

    def _bootstrap_model(self):
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.naive_bayes import MultinomialNB

            texts = [item[0] for item in TRAINING_DATA]
            categories = [item[1] for item in TRAINING_DATA]
            urgencies = [item[2] for item in TRAINING_DATA]

            self.vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words="english", lowercase=True)
            X = self.vectorizer.fit_transform(texts)

            self.category_classifier = MultinomialNB(alpha=0.5)
            self.category_classifier.fit(X, categories)

            self.urgency_classifier = MultinomialNB(alpha=0.5)
            self.urgency_classifier.fit(X, urgencies)

            self.is_trained = True
        except ImportError:
            self.is_trained = False

    def predict(self, text: str) -> Dict[str, Any]:
        """
        Classifies an emergency text into (category, urgency, confidence, keywords).
        """
        cleaned_text = text.strip()
        if not cleaned_text:
            return {
                "category": "OTHER",
                "urgency": "LOW",
                "confidence": 0.5,
                "keywords": []
            }

        # If scikit-learn model is ready, use statistical inference
        if self.is_trained and self.vectorizer is not None:
            try:
                vec = self.vectorizer.transform([cleaned_text])
                cat_probs = self.category_classifier.predict_proba(vec)[0]
                cat_classes = self.category_classifier.classes_
                best_cat_idx = np.argmax(cat_probs)
                category = cat_classes[best_cat_idx]
                confidence = float(cat_probs[best_cat_idx])

                urgency = self.urgency_classifier.predict(vec)[0]

                # Extract top detected keywords
                feature_names = self.vectorizer.get_feature_names_out()
                row = vec.toarray()[0]
                top_indices = np.argsort(row)[::-1][:4]
                keywords = [feature_names[i] for i in top_indices if row[i] > 0]

                # Apply critical urgency heuristic overrides if severe life-safety terms appear
                severe_hazard_terms = ["unconscious", "bleeding", "cardiac", "drowning", "trapped", "gas leak", "explosion", "sparking", "heart attack"]
                if any(term in cleaned_text.lower() for term in severe_hazard_terms):
                    urgency = "CRITICAL"
                    confidence = max(confidence, 0.95)

                return {
                    "category": category,
                    "urgency": urgency,
                    "confidence": round(confidence, 2),
                    "keywords": keywords
                }
            except Exception:
                pass

        # Rule-based fallback
        return self._heuristic_predict(cleaned_text)

    def _heuristic_predict(self, text: str) -> Dict[str, Any]:
        lower = text.lower()
        category = "OTHER"
        urgency = "MEDIUM"

        # Category heuristics
        if any(w in lower for w in ["blood", "wound", "insulin", "doctor", "injured", "fracture", "pain", "fever", "heart", "unconscious", "hospital"]):
            category = "MEDICAL"
        elif any(w in lower for w in ["water", "drink", "thirst", "dehydrat", "potable", "tanker"]):
            category = "WATER"
        elif any(w in lower for w in ["food", "starv", "eat", "meal", "ration", "canned", "formula", "hungry"]):
            category = "FOOD"
        elif any(w in lower for w in ["roof", "shelter", "blanket", "cot", "sleep", "cold", "tent", "evacuat"]):
            category = "SHELTER"
        elif any(w in lower for w in ["wire", "gas", "fire", "spark", "flood", "blocked", "tree", "power line", "submerged"]):
            category = "HAZARD"

        # Urgency heuristics
        if any(w in lower for w in ["critical", "dying", "unconscious", "severe", "trapped", "immediate", "drowning", "explosion", "urgent"]):
            urgency = "CRITICAL"
        elif any(w in lower for w in ["high", "danger", "running out", "need now", "broke", "baby"]):
            urgency = "HIGH"
        elif any(w in lower for w in ["minor", "inquir", "info", "when", "hours"]):
            urgency = "LOW"

        return {
            "category": category,
            "urgency": urgency,
            "confidence": 0.85,
            "keywords": [w for w in ["medical", "water", "food", "shelter", "hazard", "trapped"] if w in lower]
        }


# Singleton instance
classifier = EmergencyNLPClassifier()
