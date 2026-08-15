import json, math
def mean(xs): return sum(xs)/len(xs)
gt=json.load(open('unc_ground_truth.json'))

def build_points(wbkey, cmc_map, nominal_map):
    pts=[]
    for p in gt[wbkey]['points']:
        pdev = round(p['std_mean']-p['corrected_std'], 6)
        comps=[]
        for c in p['components']:
            comps.append({
                'label': c['label'],
                'source': c['source'],
                'distribution': c['distribution'],
                'estimate': c['estimate'],
                'ci': c.get('ci',1.0) or 1.0,
            })
        pts.append({
            'point_label': p['sheet'],
            'nominal': nominal_map[p['sheet']],
            'master_readings': p['master_readings'],
            'uut_readings': p['uut_readings'],
            'point_deviation': pdev,
            'components': comps,
            'cmc_floor': cmc_map[p['sheet']],
            'excel_reference': {
                'std_mean': p['std_mean'], 'corrected_std': p['corrected_std'],
                'uut_mean': p['uut_mean'], 's_x': p['s_x'], 's_mean': p['s_mean'],
                'combined_unc': p['excel_Uc'], 'veff': p['excel_Veff'],
                'expanded_unc': p['excel_U'],
            }
        })
    return pts

masters = [
    {"master_id":"YOG-27","name":"RTD Sensor with Indicator","manufacturer":"Nishitronics","model":"RTD-Ref","serial_number":"YOG-27","range":"-50 to 400 °C","accuracy":"±0.06 °C","resolution":"0.01 °C","cert_no":"NI2026/01/0148","cal_date":"2026-01-08","cal_due_date":"2027-01-08","traceability":"Nishitronics (NABL)","uncertainty":0.06,"status":"active"},
    {"master_id":"YOG-35","name":"Reference Indicator","manufacturer":"Nishitronics","model":"IND-35","serial_number":"YOG-35","range":"-50 to 1200 °C","accuracy":"±0.05 °C","resolution":"0.01 °C","cert_no":"NI2026/01/0148","cal_date":"2026-01-08","cal_due_date":"2027-01-08","traceability":"Nishitronics (NABL)","uncertainty":0.05,"status":"active"},
    {"master_id":"YOG-04","name":"S-Thermocouple with Indicator","manufacturer":"Nishitronics","model":"S-TC","serial_number":"YOG-04","range":"0 to 1200 °C","accuracy":"±1.021 °C","resolution":"0.1 °C","cert_no":"NI2026/01/0150","cal_date":"2026-01-08","cal_due_date":"2027-01-08","traceability":"Nishitronics (NABL)","uncertainty":1.021,"status":"active"},
    {"master_id":"YOG-36","name":"Digital Thermometer","manufacturer":"Nishitronics","model":"DT-36","serial_number":"YOG-36","range":"-50 to 400 °C","accuracy":"±0.48 °C","resolution":"0.01 °C","cert_no":"NI2026/01/0160","cal_date":"2026-01-07","cal_due_date":"2027-01-07","traceability":"Nishitronics (NABL)","uncertainty":0.48,"status":"active"},
    {"master_id":"YOG-9141","name":"FLUKE 9141 Dry Well Bath","manufacturer":"Fluke","model":"9141","serial_number":"FLK-9141","range":"50 to 650 °C","accuracy":"±0.2 °C","resolution":"0.1 °C","cert_no":"INT-9141","cal_date":"2026-01-10","cal_due_date":"2027-01-10","traceability":"Internal stability/uniformity study","uncertainty":0.16,"status":"active"},
    {"master_id":"YOG-9103","name":"FLUKE 9103 Dry Well Bath","manufacturer":"Fluke","model":"9103","serial_number":"FLK-9103","range":"-25 to 140 °C","accuracy":"±0.1 °C","resolution":"0.01 °C","cert_no":"INT-9103","cal_date":"2026-01-10","cal_due_date":"2027-01-10","traceability":"Internal stability/uniformity study","uncertainty":0.03,"status":"active"},
]

customers=[
 {"key":"itl","name":"International Tractors Limited","address":"Village Chak Gujran, P.O. Piplawala, Jalandhar Road, Hoshiarpur, Punjab-146022","contact":"Purchase Dept","email":"quality@itlsonalika.com","phone":"+91-1882-000000"},
 {"key":"iasys","name":"IASYS Technology Solutions Pvt. Ltd.","address":"Survey No. 253/3, Tirumala Industrial Estate, Hinjewadi, Pune - 411057, Maharashtra, India","contact":"Calibration Cell","email":"info@iasys.co.in","phone":"+91-20-00000000"},
]
products=[
 {"key":"itl_k","customer_key":"itl","name":"Thermocouple (with Laboratory's reference indicator)","type":"K","make":"YOG","range":"0 to 800 °C","description":"Type K thermocouple with reference indicator"},
 {"key":"iasys_rtd","customer_key":"iasys","name":"Temperature Sensor (with Laboratory's reference indicator)","type":"PT-100","make":"YOG","range":"0 to 300 °C","description":"RTD PT-100 temperature sensor with reference indicator"},
]

templates=[
 {"code":"K-IND","name":"Thermocouple K with Indicator","product_type":"K","method":"WI – TECH/11","reference_standard":"EURAMET cg-8",
  "components":[{"label":c["label"],"source":c["source"],"distribution":c["distribution"],"estimate":c["estimate"],"ci":c.get("ci",1.0) or 1.0} for c in gt["K"]["points"][0]["components"]]},
 {"code":"RTD-IND","name":"RTD (PT-100) with Indicator","product_type":"PT-100","method":"WI – TECH/11","reference_standard":"DKD-R5-1",
  "components":[{"label":c["label"],"source":c["source"],"distribution":c["distribution"],"estimate":c["estimate"],"ci":c.get("ci",1.0) or 1.0} for c in gt["RTD"]["points"][0]["components"]]},
]

jobs=[
 {"job_no":"CY/219.03","customer_key":"itl","product_key":"itl_k","serial_number":"26072764","tag_number":"",
  "cal_date":"2026-07-31","issue_date":"2026-08-01","item_received_date":"2026-07-29",
  "cert_no":"CY/2607/219.03","ulr_no":"CC324926000000567F","method":"WI – TECH/11","reference_standard":"EURAMET cg-8",
  "environmental":{"humidity":"55 ±15 % RH","ambient_temp":"25 ±4 °C"},
  "master_ids":["YOG-27","YOG-35","YOG-04","YOG-36","YOG-9141"],"template_code":"K-IND",
  "points":build_points("K",{"100":0.61,"400":0.66,"700":1.63},{"100":100.0,"400":400.0,"700":700.0})},
 {"job_no":"CY/212.01","customer_key":"iasys","product_key":"iasys_rtd","serial_number":"26060011","tag_number":"",
  "cal_date":"2026-06-03","issue_date":"2026-06-06","item_received_date":"2026-06-01",
  "cert_no":"CY/2606/212.01","ulr_no":"CC324926000000509F","method":"WI – TECH/11","reference_standard":"DKD-R5-1",
  "environmental":{"humidity":"55 ±15 % RH","ambient_temp":"25 ±4 °C"},
  "master_ids":["YOG-27","YOG-35","YOG-36","YOG-9103"],"template_code":"RTD-IND",
  "points":build_points("RTD",{"00":0.29,"50":0.29,"100":0.29,"200":0.61,"300":0.61},{"00":0.0,"50":50.0,"100":100.0,"200":200.0,"300":300.0})},
]

seed={"masters":masters,"customers":customers,"products":products,"templates":templates,"jobs":jobs}
json.dump(seed, open('/app/backend/seed_data.json','w'), indent=2)
print("wrote /app/backend/seed_data.json")
print("K comps:",len(templates[0]["components"]),"RTD comps:",len(templates[1]["components"]))
print("jobs:",[ (j["job_no"], len(j["points"])) for j in jobs])
