import json, math

def mean(xs): return sum(xs)/len(xs)
def sample_std(xs):
    n=len(xs); m=mean(xs)
    return math.sqrt(sum((x-m)**2 for x in xs)/(n-1))

def compute_point(master_readings, uut_readings, point_deviation, components):
    n = len(uut_readings)
    std_mean = mean(master_readings)
    corrected_std = std_mean - point_deviation
    uut_mean = mean(uut_readings)
    s_x = sample_std(uut_readings)
    s_mean = s_x/math.sqrt(n)
    comps=[]
    sum_ui2=0.0; typeA_ui=None
    for c in components:
        d=c['distribution']; est=c['estimate']; ci=c.get('ci',1.0)
        if d=='normal_k2': u=est/2.0
        elif d=='rect_root3': u=est/math.sqrt(3)
        elif d=='typeA':
            est=s_x; u=s_x/math.sqrt(n)
        else: raise ValueError(d)
        ui=u*ci; sum_ui2+=ui*ui
        if d=='typeA': typeA_ui=ui
        comps.append({**c,'estimate':est,'std_unc':u,'ui':ui,'ui_sq':ui*ui})
    Uc=math.sqrt(sum_ui2)
    veff = (Uc**4)/((typeA_ui**4)/(n-1)) if typeA_ui else float('inf')
    k = 2.0 if veff>30 else 2.0
    U = k*Uc
    deviation = uut_mean - corrected_std
    return dict(std_mean=std_mean,corrected_std=corrected_std,uut_mean=uut_mean,
                s_x=s_x,s_mean=s_mean,Uc=Uc,Veff=veff,k=k,U=U,deviation=deviation)

gt=json.load(open('unc_ground_truth.json'))
ok=True
for wbname,wb in gt.items():
    for p in wb['points']:
        pdev = p['std_mean']-p['corrected_std']
        r=compute_point(p['master_readings'],p['uut_readings'],pdev,p['components'])
        def chk(a,b,tol=1e-9):
            return abs(a-b)<=tol*max(1,abs(b))
        checks={
          'std_mean':(r['std_mean'],p['std_mean']),
          's_x':(r['s_x'],p['s_x']),
          's_mean':(r['s_mean'],p['s_mean']),
          'uut_mean':(r['uut_mean'],p['uut_mean']),
          'Uc':(r['Uc'],p['excel_Uc']),
          'Veff':(r['Veff'],p['excel_Veff']),
          'U':(r['U'],p['excel_U']),
        }
        for name,(app,ex) in checks.items():
            good=chk(app,ex,1e-6)
            if not good:
                ok=False
                print(f"MISMATCH {wbname} {p['sheet']} {name}: app={app} excel={ex}")
        print(f"{wbname} pt {p['sheet']}: Uc app={r['Uc']:.10f} excel={p['excel_Uc']:.10f} | U app={r['U']:.6f} excel={p['excel_U']:.6f} | Veff app={r['Veff']:.2f} excel={p['excel_Veff']:.2f}")
print("ALL MATCH" if ok else "FAILURES ABOVE")
