import xlrd, sys
for path in sys.argv[1:]:
    print("="*100)
    print("WORKBOOK:", path)
    wb = xlrd.open_workbook(path, formatting_info=False)
    print("SHEETS:", wb.sheet_names())
    for sh in wb.sheets():
        print("\n" + "#"*80)
        print("SHEET:", sh.name, "rows", sh.nrows, "cols", sh.ncols)
        for r in range(sh.nrows):
            for c in range(sh.ncols):
                cell = sh.cell(r, c)
                if cell.value == '' or cell.value is None:
                    continue
                colname = xlrd.colname(c)
                print(f"  {colname}{r+1}: {cell.value!r}")
