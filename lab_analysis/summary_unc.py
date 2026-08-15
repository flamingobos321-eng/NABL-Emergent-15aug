import xlrd, sys
for path in sys.argv[1:]:
    print("FILE:", path.split('/')[-1])
    wb = xlrd.open_workbook(path)
    for sh in wb.sheets():
        vals={}
        for r in range(sh.nrows):
            a=sh.cell(r,0).value
            k=sh.cell(r,10).value
            g=sh.cell(r,6).value
            if isinstance(a,str):
                if 'Combined Std Unc' in a: vals['Uc']=k
                if 'Expanded' in str(sh.cell(r,5).value): vals['U_exp']=k
                if 'Deg of Freedom Veff' in a: vals['Veff']=k
        # corrected std D12 and xbar G12
        for r in range(sh.nrows):
            if sh.cell(r,0).value=='Average →':
                vals['CorrSTD_D']=sh.cell(r,3).value
                vals['Xbar_G']=sh.cell(r,6).value
        print(f"  sheet {sh.name}: CorrectedSTD={vals.get('CorrSTD_D')}, Xbar(UUC)={vals.get('Xbar_G')}, Uc={vals.get('Uc')}, U_expanded={vals.get('U_exp')}")
