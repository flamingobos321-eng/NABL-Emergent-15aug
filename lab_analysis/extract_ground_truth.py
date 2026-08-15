import xlrd, json, math

DIST_MAP = {
    'BN / 2': 'normal_k2',
    'BR /Ö3': 'rect_root3',
    'A /Ö5': 'typeA',
}

def norm(s):
    return str(s).replace('\n',' ').strip()

def parse_sheet(sh):
    data = {'point_label': None, 'master_readings': [], 'uut_readings': [],
            'std_mean': None, 'corrected_std': None, 'uut_mean': None,
            's_x': None, 's_mean': None, 'components': [],
            'excel_Uc': None, 'excel_Veff': None, 'excel_U': None,
            'ref_master': None, 'ref_unc': None, 'ref_dev': None}
    for r in range(sh.nrows):
        A = norm(sh.cell(r,0).value)
        Dc = norm(sh.cell(r,3).value)
        Fc = norm(sh.cell(r,5).value)
        # point label
        if A == 'Unit Under Calibration (UUC)':
            data['point_label'] = Dc
        if A == 'Reference':
            data['ref_master'] = norm(sh.cell(r,1).value)
            data['ref_unc'] = sh.cell(r,5).value
            data['ref_dev'] = sh.cell(r,9).value
        if A.startswith('Obs'):
            c = sh.cell(r,2).value; f = sh.cell(r,5).value
            if isinstance(c,(int,float)): data['master_readings'].append(c)
            if isinstance(f,(int,float)): data['uut_readings'].append(f)
        if A == 'Average →':
            data['std_mean'] = sh.cell(r,2).value
            data['corrected_std'] = sh.cell(r,3).value
            data['uut_mean'] = sh.cell(r,6).value
            data['s_x'] = sh.cell(r,9).value
            data['s_mean'] = sh.cell(r,10).value
        # budget rows: distribution string present in col F
        distraw = norm(sh.cell(r,5).value)
        if distraw in DIST_MAP:
            data['components'].append({
                'label': A,
                'source': norm(sh.cell(r,1).value),
                'estimate': sh.cell(r,3).value,
                'limit': sh.cell(r,4).value,
                'distribution': DIST_MAP[distraw],
                'dist_raw': distraw,
                'std_unc': sh.cell(r,6).value,
                'ci': sh.cell(r,7).value,
                'ui': sh.cell(r,8).value,
                'dof': sh.cell(r,9).value,
                'ui_sq': sh.cell(r,10).value,
            })
        if 'Combined Std Unc' in A:
            data['excel_Uc'] = sh.cell(r,10).value
        if 'Deg of Freedom Veff' in A:
            data['excel_Veff'] = sh.cell(r,10).value
        if 'Expanded Uncertainty' in Fc:
            data['excel_U'] = sh.cell(r,10).value
    return data

def parse_wb(path, name):
    wb = xlrd.open_workbook(path)
    out = {'name': name, 'points': []}
    for sh in wb.sheets():
        out['points'].append({'sheet': sh.name, **parse_sheet(sh)})
    return out

base = 'extracted/Lab docs for software/'
result = {
    'K': parse_wb(base+'FTECH22R0 (Uncertainty Calculation sheet)-K with Indicator.xls', 'K'),
    'RTD': parse_wb(base+'FTECH22R0 (Uncertainty Calculation sheet)-RTD with Indicator.xls', 'RTD'),
}
with open('unc_ground_truth.json','w') as f:
    json.dump(result, f, indent=2)
print(json.dumps(result, indent=2)[:4000])
