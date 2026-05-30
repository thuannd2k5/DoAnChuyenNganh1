# DFA Selenium Test Automation (Draft README)

README nay la ban tom tat nhanh, chua day du, theo 3 nhom trang thai:
- `Da co`
- `Chua co`
- `Can cai thien`

## 1) Chuc nang Da co

- DFA Engine:
  - Validator JSON + DFA rules (`engine/validator.py`)
  - DFS path generator + CSV export (`engine/dfs_generator.py`)
  - Graph visualization + PNG export (`engine/visualize_graph.py`)
  - Visual DFA Builder tren Streamlit (`ui/app.py`)
  - Import/Export model JSON (`ui/app.py`)
- Visual Mapping Builder:
  - Extract action tu transitions (`ui/app.py`)
  - Form mapping theo action, ho tro add/remove/reorder step (`ui/app.py`)
  - Step types: `click`, `input`, `assert_text`, `assert_url`, `wait`, `screenshot`
  - Selector types: `id`, `css`, `xpath`
  - Realtime JSON preview + validate + save/download mapping (`ui/app.py`)
- Selenium Executor:
  - Chay path tu CSV + mapping (`executor/selenium_executor.py`)
  - Assertions (`assert_text`, `assert_url_contains`, `assert_element_visible`)
  - Wait bang `WebDriverWait + expected_conditions`
  - Execution summary JSON (`reports/execution_summary.json`)
  - Run integration tren Streamlit (nut `RUN` goi `run_framework`)
- Reports & Analytics:
  - Dashboard tren UI (summary/failures/analytics)
  - CSV paths export (`reports/csv/*.csv`)
- Demo & Validation:
  - Demo URL mac dinh: SauceDemo (`ui/app.py`)
  - Co model >=5 states, >=6 transitions (vi du `sample_assets/models/checkout.json`)
  - End-to-end pipeline da duoc noi:
    - DFA -> paths -> mapping -> Selenium -> report
  - Co nhanh negative trong demo model (vi du `add_failed`)

## 2) Chuc nang Chua co

- Nen tang ly thuyet/bao cao:
  - Chua co chuong gioi thieu DFA, MBT, DFS traversal, Selenium architecture trong README/report.
- Reports & Analytics:
  - Execution history theo timestamp moi lan run (chua co co che luu version report theo lan chay)
  - HTML report export sau moi run
  - Regression chart so sanh nhieu lan run
  - Test coverage report (% transitions covered, % paths passed)
- Selenium Executor:
  - Retry mechanism truoc khi danh dau FAIL
- Code quality:
  - `requirements.txt` (hoac `pyproject.toml`) chua co
  - Unit tests cho engine (`tests/` dang trong)
- Demo & Validation:
  - Slide thuyet trinh chua co trong repo
  - Tai lieu Q&A chua co trong repo

## 3) Chuc nang Can cai thien

- Mapping/Test data:
  - Data-driven chua tach bo du lieu ro rang theo dataset (hien value dang hardcode trong mapping)
  - Ket qua chua tach theo truc `path x dataset`
- Screenshot:
  - Hien tai chup khi FAIL (va co step type `screenshot`), chua tu dong chup moi step.
- Mapping demo:
  - Can dong bo ten action giua DFA path va mapping de tranh loi `Action not found`.
- Code quality:
  - Docstring module/function chua day du
  - `README.md` nay moi o muc draft, can bo sung huong dan cai dat/chay chi tiet
  - Credential demo (`standard_user`, `secret_sauce`) dang xuat hien trong JSON mau/report, nen dua qua config/env cho sach code

## 4) Cau truc chinh

- `engine/`: DFA builder logic, validator, DFS, graph
- `executor/`: Selenium executor + assertions
- `controller/`: integration pipeline
- `ui/`: Streamlit app
- `sample_assets/`: model/mapping mau
- `reports/`: csv/graph/screenshot/summary output
- `tests/`: unit tests (hien dang chua co test)

## 5) Huong dan chay nhanh (tam thoi)

```bash
pip install selenium pytest webdriver-manager streamlit pandas networkx matplotlib
streamlit run ui/app.py
```

Luu y: day la README tam thoi de tong hop trang thai hien tai. Se can mot ban README day du hon cho nop/bao ve.
