import json
import pickle
import os
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix

DATASET = [
    # MEDICAL
    ("Severe chest pain and difficulty breathing after building collapse", "MEDICAL"),
    ("Diabetic patient trapped without insulin for two days, unconscious", "MEDICAL"),
    ("Elderly woman fell and broke hip, heavy bleeding needs ambulance", "MEDICAL"),
    ("Severe lacerations from shattered window glass, need stitches and sterile gauze", "MEDICAL"),
    ("Child running 104 fever, shivering with dehydration and seizures", "MEDICAL"),
    ("Need prescription heart medication refills after evacuation for cardiac patient", "MEDICAL"),
    ("Minor cuts and scrapes from debris, first aid supplies requested", "MEDICAL"),
    ("Compound fracture of leg, victim immobilized under fallen beam", "MEDICAL"),
    ("Asthmatic person in respiratory distress, emergency inhaler lost in flood", "MEDICAL"),
    ("Hypothermia symptoms in 3 children, medical clinic requested", "MEDICAL"),
    ("Pregnant woman in active labor, need obstetrician or emergency paramedic", "MEDICAL"),
    ("Deep puncture wound from rusty nail, tetanus injection and sterile bandages", "MEDICAL"),
    ("Head trauma and severe concussion following wall collapse", "MEDICAL"),
    ("Multiple burn victims from propane heater flash fire need burn dressings", "MEDICAL"),
    ("Urgent stroke medication and blood thinners needed immediately", "MEDICAL"),
    ("Unconscious male found in flooded alleyway, pulse weak, need EMS", "MEDICAL"),
    ("Dialysis patient missed two sessions due to severed roads, urgent medical evacuation", "MEDICAL"),
    ("Severe allergic anaphylactic shock reaction, epinephrine auto-injector needed", "MEDICAL"),
    ("Tourniquet applied to severed artery, paramedic transport critical", "MEDICAL"),
    ("Infection spreading around open surgical wound, antibiotics required", "MEDICAL"),

    # WATER
    ("Drinking water completely contaminated with sewage, no clean water for 200 people", "WATER"),
    ("Dehydrated infants and mothers, municipal water main ruptured, urgent water needed", "WATER"),
    ("Running out of bottled drinking water at neighborhood shelter, 50 people remaining", "WATER"),
    ("Need potable water purification tablets or water filtration unit", "WATER"),
    ("Tap water smells like sulfur, request water tanker dispatch", "WATER"),
    ("Low water pressure in building, inquiring about water distribution times", "WATER"),
    ("Water supply exhausted at community center, 120 evacuees need bottled water", "WATER"),
    ("Reservoir contaminated with flood runoff, boil water advisory in effect", "WATER"),
    ("Emergency water pallets needed for primary relief station", "WATER"),
    ("Residents drawing creek water, urgent need for chlorine tablets", "WATER"),
    ("Elderly complex has no running water, elderly unable to carry buckets", "WATER"),
    ("Desperately need 500 liters of drinking water for field hospital", "WATER"),
    ("Clean water storage tank punctured and empty", "WATER"),
    ("Need portable water bladders and hand pump dispensers", "WATER"),
    ("Infants showing signs of severe thirst and dehydration", "WATER"),

    # FOOD
    ("No food for 3 days, family with three young toddlers starving in attic", "FOOD"),
    ("Community hall kitchen exhausted all canned goods, 150 refugees need meals", "FOOD"),
    ("Requesting dry rations, rice, beans, and baby formula", "FOOD"),
    ("Need non-perishable ready-to-eat meals (MREs) for stranded rescue crew", "FOOD"),
    ("Looking for food pantry open hours near downtown", "FOOD"),
    ("Emergency baby formula and infant purees urgently needed", "FOOD"),
    ("Canned food pantry inundated with mud, all food spoiled", "FOOD"),
    ("Elderly couple stranded without food rations since Tuesday", "FOOD"),
    ("Shelter kitchen needs rice, lentils, and cooking oil for dinner service", "FOOD"),
    ("High calorie protein bars requested for search and rescue volunteers", "FOOD"),
    ("Children complaining of severe hunger, milk and bread needed", "FOOD"),
    ("Requesting pallets of MRE rations for flood victims", "FOOD"),
    ("Gluten-free rations requested for celiac evacuee with medical needs", "FOOD"),
    ("No groceries or food supplies in isolated hilltop neighborhood", "FOOD"),
    ("Community center feeding 300 hot meals daily, supplies running critically low", "FOOD"),

    # SHELTER
    ("Roof ripped off by tornado, 6 people exposed to torrential freezing rain", "SHELTER"),
    ("Flood waters rising above first floor ceiling, need immediate boat rescue to dry shelter", "SHELTER"),
    ("Apartment basement flooded, displaced family of five needs emergency shelter bed", "SHELTER"),
    ("Need blankets, sleeping bags, and cots for local gymnasium shelter", "SHELTER"),
    ("Where is the nearest pet-friendly evacuation shelter?", "SHELTER"),
    ("House uninhabitable after seismic tremor, family sleeping in driveway car", "SHELTER"),
    ("Emergency tent encampment needs 40 family dome tents and tarps", "SHELTER"),
    ("Shelter at elementary school at 100% capacity, need secondary site opened", "SHELTER"),
    ("Temporary warming center needed as nighttime temperature drops below freezing", "SHELTER"),
    ("Displaced tenants seeking emergency housing voucher assistance", "SHELTER"),
    ("Need dry floor mats and thermal sleeping pads for 80 evacuees", "SHELTER"),
    ("Structural crack in wall, building declared unsafe by fire marshal, need relocation", "SHELTER"),
    ("Elderly care facility evacuated, need 30 handicap-accessible cots", "SHELTER"),
    ("Seeking safe shelter away from active wildfire evacuation zone", "SHELTER"),
    ("Storm surge breached seawall, ground floors flooded, residents need dry refuge", "SHELTER"),

    # HAZARD
    ("Live electrical high-voltage wire downed in flooded street, sparking actively", "HAZARD"),
    ("Strong gas smell near collapsed residential duplex, risk of explosion", "HAZARD"),
    ("Main bridge approach cracked and submerged, road completely impassable", "HAZARD"),
    ("Large oak tree blocking two-lane emergency route on Elm Street", "HAZARD"),
    ("Streetlights non-functional at intersection, minor traffic slowdown", "HAZARD"),
    ("Severe mudslide blocking mountain access pass, cars trapped between debris", "HAZARD"),
    ("Chemical smell and yellow liquid leaking from overturned tanker truck", "HAZARD"),
    ("Sinkhole opening up in middle of intersection after water main collapse", "HAZARD"),
    ("Dam spillway overflowing, structural failure possible within 6 hours", "HAZARD"),
    ("Downed power transformer leaking mineral oil into storm drain", "HAZARD"),
    ("Collapsed brick chimney dangling precariously over pedestrian walkway", "HAZARD"),
    ("Flash flood washed out culvert, asphalt collapsed across highway", "HAZARD"),
    ("Propane storage tank floating in fast-moving flood current", "HAZARD"),
    ("Power lines draped across school bus, occupants unable to safely exit", "HAZARD"),
    ("Severe gas pipeline fracture, emergency valve shutoff required immediately", "HAZARD"),
]


def train_and_evaluate():
    texts = [item[0] for item in DATASET]
    labels = [item[1] for item in DATASET]

    X_train, X_test, y_train, y_test = train_test_split(
        texts, labels, test_size=0.25, random_state=42, stratify=labels
    )

    pipeline = Pipeline([
        ('tfidf', TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, stop_words='english', min_df=1)),
        ('clf', LogisticRegression(C=5.0, max_iter=200))
    ])

    pipeline.fit(X_train, y_train)

    y_pred = pipeline.predict(X_test)

    report_dict = classification_report(y_test, y_pred, output_dict=True)
    report_text = classification_report(y_test, y_pred)

    print("=" * 60)
    print("RELAY Emergency Triage Classifier Evaluation Report")
    print("=" * 60)
    print(report_text)

    # Save model and metrics
    output_dir = os.path.dirname(__file__)
    model_path = os.path.join(output_dir, "model.pkl")
    with open(model_path, "wb") as f:
        pickle.dump(pipeline, f)

    metrics_path = os.path.join(output_dir, "evaluation_report.json")
    with open(metrics_path, "w") as f:
        json.dump(report_dict, f, indent=2)

    print(f"Model saved to: {model_path}")
    print(f"Metrics saved to: {metrics_path}")


if __name__ == "__main__":
    train_and_evaluate()
