# BB84: mô phỏng và phân tích an toàn cho bài tập lớn

Dự án dành cho nhóm 5 sinh viên học Lý thuyết mật mã. Mã nguồn mô phỏng chuẩn bị và đo các trạng thái BB84, sàng lọc cơ sở, Eve chặn–đo–gửi lại, nhiễu, mất tín hiệu và lấy mẫu QBER. Sáu thí nghiệm tạo dữ liệu, đồ thị và báo cáo HTML để nhóm phân tích và thuyết trình.

**Mục tiêu là hiểu và kiểm chứng mô hình. Chương trình chưa tạo khóa bí mật dùng được trong thực tế:** chưa triển khai xác thực kênh cổ điển, hòa giải thông tin/sửa lỗi, kiểm tra khóa sau sửa lỗi và khuếch đại tính riêng tư. Thông báo `continue_postprocessing` chỉ có nghĩa tiếp tục bước hậu xử lý trong minh họa; không có nghĩa khóa đã an toàn.

## 1. Bắt đầu trên Windows

Nếu nhận toàn bộ thư mục đã có `.venv`, có thể nhấp đúp **`RUN_DEMO.cmd`**, **`RUN_EXPERIMENTS.cmd`** hoặc **`RUN_TESTS.cmd`**. Khi chuyển sang máy khác, tạo lại môi trường bằng **`SETUP_WINDOWS.cmd`**; không sao chép `.venv` giữa các máy.

Để chủ động xem lỗi và thay tham số, mở PowerShell trong thư mục dự án. Dự án yêu cầu **Python 3.10 trở lên, khuyến nghị 3.12**. Không cần MATLAB, phần cứng lượng tử hoặc tài khoản IBM để chạy phần chính.

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m bb84 demo --seed 84 --signals 10000
.\.venv\Scripts\python.exe -m bb84 experiments --preset quick --output results --seed 84
```

Các lệnh gọi thẳng Python của môi trường ảo, nên không cần thay đổi Execution Policy hay chạy `Activate.ps1`. Trên Linux/macOS, thay đường dẫn `.\.venv\Scripts\python.exe` bằng `.venv/bin/python`.

Sau khi chạy experiments, mở `results/report.html` bằng trình duyệt. Đây là tệp cục bộ, không cần máy chủ web. Đọc `results/RESULTS.md` để đưa kết quả vào báo cáo. Chạy bản đủ số lần lặp sau khi đã hiểu bản nhanh:

```powershell
.\.venv\Scripts\python.exe -m bb84 experiments --preset standard --output results-standard --seed 84
```

| Chế độ | Số tín hiệu mỗi lần chạy | Số lần lặp mỗi cấu hình | Cách dùng |
|---|---:|---:|---|
| `quick` | 5.000 | 30 | Kiểm tra môi trường, xem xu hướng, demo |
| `standard` | 20.000 | 150 | Thu thập kết quả cho báo cáo |

Riêng thí nghiệm 4 dùng 500 lần lặp/điểm ở `quick`, 2.000 lần lặp/điểm ở `standard`, với khối `N=max(512,8m)`; hai tham số ghi đè `--signals`/`--repetitions` không thay đổi thí nghiệm này. Các thí nghiệm chính yêu cầu N ≥ 64 và số lần lặp ≥ 2.

Hai preset phục vụ thời gian tính toán và độ ổn định Monte Carlo. Chúng không tương ứng với hai cấp độ chứng nhận an toàn.

**Cách chạy hiệu quả:** chạy tests và `quick` một lần để kiểm tra môi trường; dùng `standard` để chốt bộ kết quả. Khi thay một giả định, chạy `simulate` riêng trước; chỉ chạy lại toàn bộ sáu thí nghiệm nếu cần so sánh. Dùng thư mục đầu ra khác nhau cho các cấu hình/seed và giữ CSV cùng hình. Không cần tăng số tín hiệu lên hàng triệu để làm bài này: chi phí tăng gần tuyến tính theo số tín hiệu và số lần lặp, trong khi sai số Monte Carlo giảm chậm hơn.

Có thể điều chỉnh khối lượng tính toán mà vẫn giữ bộ sáu thí nghiệm:

```powershell
.\.venv\Scripts\python.exe -m bb84 experiments --preset standard --signals 10000 --repetitions 50 --output results-custom --seed 85
```

Tăng `--signals` giảm dao động trong mỗi lần mô phỏng; tăng `--repetitions` giúp ước lượng trung bình/phân bố giữa các lần chạy ổn định hơn. Đây là hai mục tiêu khác nhau. Thời gian chạy thực tế phụ thuộc CPU, I/O và lần khởi tạo font; xem thông tin mỗi lần chạy, không xem một con số thời gian là cam kết trên mọi máy.

### Các công cụ tùy chọn

- **JupyterLab**: thực hành từng bước trong `notebooks/BB84_tutorial.ipynb`.
- **Qiskit và Qiskit Aer**: kiểm tra xác suất đo bốn trạng thái bằng mạch một qubit. Phần này bổ sung cho mô phỏng NumPy; không cần để chạy sáu thí nghiệm.
- **Git**, **Zotero**, **Word/LaTeX**, **PowerPoint**: quản lý phiên bản, tài liệu tham khảo, viết báo cáo và slide.

Lệnh cài phần tùy chọn và chạy kiểm tra mạch:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-optional.txt
.\.venv\Scripts\python.exe -m bb84 qiskit-check --shots 4096 --seed 84
.\.venv\Scripts\python.exe -m jupyterlab
```

Phần mô phỏng chính chỉ dùng NumPy và Matplotlib; không yêu cầu SciPy hoặc pandas. Thông tin môi trường của mỗi lần chạy thí nghiệm được ghi trong `metadata.json`; lưu tệp này cùng dữ liệu để tái lập kết quả. Sau khi mở JupyterLab, chọn `notebooks/BB84_tutorial.ipynb`, chọn kernel Python của `.venv`, rồi dùng **Kernel → Restart Kernel and Run All Cells**. Ô đầu in `sys.executable` để kiểm tra môi trường đang chạy.

## 2. BB84 làm gì?

Alice và Bob muốn cùng có một chuỗi bit bí mật. Alice chọn ngẫu nhiên bit và cơ sở; Bob chọn cơ sở đo độc lập. Hai người công bố **cơ sở**, giữ các vị trí trùng cơ sở rồi công bố một **mẫu bit** để ước lượng lỗi. Bit đã công bố trong mẫu bị loại khỏi phần có thể dùng tạo khóa. Mọi trao đổi cổ điển của giao thức thật phải được xác thực. Nếu thống kê phù hợp, họ còn phải sửa lỗi, kiểm tra tính đúng và rút ngắn khóa để giảm thông tin Eve.

| Cơ sở | Bit 0 | Bit 1 | Ý nghĩa đo |
|---|---|---|---|
| Z | ∣0⟩ | ∣1⟩ | Đo đúng cơ sở cho đúng bit trong trường hợp lý tưởng |
| X | ∣+⟩ = (∣0⟩ + ∣1⟩)/√2 | ∣−⟩ = (∣0⟩ − ∣1⟩)/√2 | Đo khác cơ sở cho hai kết quả với xác suất 1/2 |

Có thể biểu diễn bốn trạng thái bằng phân cực H/V và D/A. Dự án dùng mô hình qubit, không mô phỏng chi tiết laser, photon đa hạt, detector hay thiết bị quang.

Eve trong bài thực hành chặn một phần tín hiệu, chọn ngẫu nhiên cơ sở đo rồi gửi trạng thái tương ứng đến Bob. Khi Eve chặn toàn bộ, chọn đều hai cơ sở và kênh lý tưởng, QBER trên các vị trí trùng cơ sở tiến gần **25%**. Khi tỷ lệ chặn là (f), giá trị kỳ vọng là (f/4). Điều này giải thích một tấn công cụ thể; nó không bao quát mọi chiến lược lượng tử của Eve.

Xem [giả định, công thức và giới hạn](docs/SCIENCE.md) trước khi diễn giải đồ thị.

## 3. Chạy demo và dùng API

```powershell
.\.venv\Scripts\python.exe -m bb84 demo --seed 84 --signals 10000
.\.venv\Scripts\python.exe -m bb84 demo --seed 84 --signals 16 --trace
```

Demo in kết quả của ba tình huống: kênh lý tưởng, có nhiễu và có Eve. `--trace` dùng cho chuỗi ngắn để quan sát bit, cơ sở, vị trí được giữ và mẫu kiểm tra. Chuỗi 16 bit chỉ minh họa thao tác; với ít mẫu, khoảng bất định QBER rất rộng hoặc không đủ dữ liệu.

Để chạy một cấu hình tự chọn và lưu tóm tắt:

```powershell
.\.venv\Scripts\python.exe -m bb84 simulate --signals 20000 --eve 0.5 --noise 0.02 --noise-model depolarizing --loss 0.1 --sample-fraction 0.2 --seed 84 --output results-single
.\.venv\Scripts\python.exe -m bb84 simulate --signals 16 --eve 1 --seed 84 --trace --output results-trace
.\.venv\Scripts\python.exe -m bb84 simulate --help
```

`summary.json` chứa cấu hình, các số đếm, QBER, khoảng Wilson và quyết định. Khi bật `--trace`, `trace.csv` lưu bảng từng tín hiệu phục vụ giải thích; dữ liệu này là quan sát nội bộ của mô phỏng và không được công bố như vậy trong giao thức thật. Khi cần số bit mẫu cố định, dùng `--sample-size 500`; tham số này ưu tiên hơn `--sample-fraction`. Nếu mẫu yêu cầu lớn hơn lượng sifted data, chương trình báo thiếu dữ liệu.

```python
from bb84 import BB84Config, simulate

config = BB84Config(
    n_signals=10_000,
    eve_fraction=0.5,
    noise_probability=0.02,
    noise_model="depolarizing",
    loss_probability=0.1,
    basis_probability_z=0.5,
    sample_fraction=0.2,
    abort_threshold=0.11,
    confidence=0.95,
)
result = simulate(config, seed=84)
print(result.summary())
```

| Tham số | Ý nghĩa |
|---|---|
| `n_signals` | Số tín hiệu Alice phát |
| `eve_fraction` | Xác suất mỗi tín hiệu bị Eve chặn–đo–gửi lại |
| `noise_model` | `depolarizing` hoặc `readout_flip` |
| `noise_probability` | Tham số (p) của mô hình nhiễu đã chọn; hai mô hình có cách quy đổi QBER khác nhau |
| `loss_probability` | Xác suất mất tín hiệu độc lập trong mô hình |
| `basis_probability_z` | Xác suất chọn Z của Alice và Bob; 0,5 là BB84 cân bằng; chọn 0 hoặc 1 không còn dữ liệu kiểm tra ở cơ sở bổ sung |
| `sample_fraction` | Tỷ lệ lấy mẫu từ chuỗi sau sifting, nằm trong (0,1); số mẫu được làm tròn xuống |
| `sample_size` | Số bit mẫu nguyên dương; khi có giá trị sẽ ưu tiên hơn `sample_fraction` |
| `abort_threshold` | Mốc QBER minh họa, mặc định 0,11 |
| `confidence` | Mức khoảng Wilson dùng cho quyết định giảng dạy, mặc định 0,95 |
| `seed` | Hạt giống RNG truyền cho `simulate`, giúp tái lập thí nghiệm |

Tách bạch các kết quả: QBER toàn bộ chuỗi sifted là thông tin **chỉ bộ mô phỏng biết**; trong giao thức thật Alice và Bob dùng mẫu được công bố. Mẫu công bố và dữ liệu chẩn đoán của simulator không được xem là khóa bí mật.

Trạng thái quyết định là `continue_postprocessing`, `abort` hoặc `insufficient_data`. Chương trình dùng cận trên Wilson so với ngưỡng để minh họa một quyết định có xét bất định; đây không phải kiểm định chứng nhận an toàn QKD. Ngay cả khi trả về `continue_postprocessing`, chưa có bước trích xuất khóa nào được thực hiện.

## 4. Thí nghiệm và cách đọc kết quả

Mỗi lần chạy `experiments` lưu sáu hình ở định dạng PNG và PDF, các CSV dữ liệu thô/tổng hợp, `metadata.json`, `report.html` và `RESULTS.md` trong thư mục đầu ra.

| Thí nghiệm | Câu hỏi cần trả lời | Kỳ vọng cần đối chiếu |
|---|---|---|
| 1. QBER theo tỷ lệ Eve, nhiều mức nhiễu | QBER tăng theo mức chặn thế nào? Nhiễu nền ảnh hưởng ra sao? | Không nhiễu: (Q=f/4). Có nhiễu: không cộng đơn giản hai xác suất lỗi |
| 2. QBER theo tham số nhiễu | Cùng (p), hai mô hình có giống nhau không? | Depolarizing: (Q=p/2); readout flip: (Q=p), khi không có Eve |
| 3. Bất định theo cỡ mẫu | Nhiều mẫu hơn đổi độ tin cậy và phần dữ liệu còn lại thế nào? | Mẫu lớn thường làm khoảng hẹp hơn nhưng tiêu tốn nhiều bit sifted |
| 4. Xác suất thấy ít nhất một lỗi | Khi nào mẫu bỏ sót lỗi? | Trong mô hình i.i.d.: (1-(1-Q)^m); thấy lỗi không đồng nghĩa xác định được Eve |
| 5. Tỷ lệ giữ lại theo mất tín hiệu | Mất tín hiệu làm giảm sản lượng hay tự gây lỗi bit? | Sifted/phát ≈ ((1-L)[p_Z^2+(1-p_Z)^2]), mất độc lập không tự gây QBER |
| 6. Tỷ lệ khóa tiệm cận tham chiếu | QBER và hiệu suất sửa lỗi ảnh hưởng bound tham chiếu ra sao? | (r_∞=[1-h_2(Q)-f_{EC}h_2(Q)]_+), với đầy đủ giả định trong SCIENCE.md |

Đồ thị 6 là **đường tham chiếu lý thuyết**, không phải số bit bí mật mà mô phỏng đã trích xuất. Các hình còn lại là thí nghiệm Monte Carlo hoặc đối chiếu xác suất trong mô hình. Không gọi cả sáu hình là kết quả đo trên máy tính lượng tử/phần cứng QKD.

Khi đưa vào báo cáo, mỗi hình cần có: câu hỏi nghiên cứu; biến thay đổi và biến giữ cố định; đơn vị trục; (N), số lần lặp và seed; ý nghĩa thanh/khoảng sai số đúng theo chú thích; kết luận; một giới hạn. Không chỉ đặt hình rồi nhận xét “đường tăng/giảm”.

## 5. Kế hoạch 6 tuần cho nhóm 5 sinh viên

| Tuần | Công việc chung | Sản phẩm kiểm tra |
|---|---|---|
| 1 | Đọc BB84 gốc và phần nhập môn của review; phân biệt bit, qubit, cơ sở; thống nhất phạm vi | Bảng bốn trạng thái, sơ đồ giao thức, bảng ký hiệu |
| 2 | Phân tích intercept–resend, nhiễu, mất tín hiệu và giả định xác thực | Tự suy ra (f/4), đặc tả mô hình, ba câu hỏi nghiên cứu |
| 3 | Chạy notebook, đọc source, chạy kiểm thử, giải thích từng cột trace | Bản mô phỏng tái lập được và README đã kiểm tra trên máy thứ hai |
| 4 | Chạy preset standard; kiểm tra đường kỳ vọng, cỡ mẫu và lặp Monte Carlo | Dữ liệu CSV, ít nhất ba đồ thị có phân tích, ghi chú bất thường |
| 5 | Phân tích giới hạn 11%, finite-key và khoảng cách với triển khai thực | Bản báo cáo đầy đủ, danh mục tham khảo và kết luận có điều kiện |
| 6 | Hoàn thiện mã/slide; diễn tập bảo vệ, demo; mọi thành viên giải thích được giao thức | Gói nộp tái lập được, thuyết trình 10–12 phút, demo 3–5 phút |

| Thành viên | Vai trò chính | Trách nhiệm cụ thể và bàn giao |
|---|---|---|
| SV1 | Protocol & quantum foundations | Bốn trạng thái, phép đo, sifting; kiểm tra notebook; giải thích vì sao công bố cơ sở không tương đương công bố bit |
| SV2 | Security/cryptographic analysis | Intercept–resend, xác thực, giả định 11%, lỗi và giới hạn; rà soát mọi câu “an toàn” trong báo cáo |
| SV3 | Mathematical/system model | Định nghĩa (N,m,Q,f,p,L); suy ra đường kỳ vọng và điều kiện; đối chiếu mô hình với mã |
| SV4 | Simulation/coding | Tổ chức chạy, cấu hình, seed, tests, dữ liệu và README; hỗ trợ tái lập trên máy khác |
| SV5 | Results, report & presentation | Tổng hợp CSV/hình, phân tích sai số, citation, report, slide và demo |

Mỗi người có người khác đọc chéo sản phẩm. Phân công không thay thế yêu cầu mọi thành viên phải nắm toàn bộ luồng BB84 và giới hạn kết luận.

## 6. Đối chiếu yêu cầu đề bài

Ảnh yêu cầu ghi cả **8–10 trang** ở phần ví dụ và **15–20 trang** ở dòng sản phẩm bắt buộc. Kho mã này dùng 15–20 trang làm giả định lập kế hoạch, không tự thay đổi quy định môn học. Giảng viên nên công bố một mốc thống nhất, kể cả việc có tính phụ lục/tài liệu tham khảo hay không. Ảnh cũng ghi 2–3 đồ thị ở ví dụ và tối thiểu 3 đồ thị/bảng ở yêu cầu cuối; chọn ít nhất 3 kết quả có phân tích đáp ứng cả hai.

| Yêu cầu | Thành phần hỗ trợ trong kho mã | Phần nhóm phải hoàn thiện |
|---|---|---|
| Theory: nguyên lý và nền tảng mật mã/lượng tử | SCIENCE.md; notebook; bảng trạng thái | Viết lại bằng hiểu biết của nhóm, liên hệ môn học |
| Security: Eve và phát hiện/chống tấn công | Intercept–resend; lấy mẫu; phân tích giới hạn | Giải thích xác thực, EC/PA; phân biệt mô phỏng tấn công với proof |
| Simulation: Python/MATLAB đơn giản | Python CLI, core, notebook, kiểm tra Qiskit tùy chọn | Hiểu mã, chạy lại, lưu cấu hình và dữ liệu |
| Results: ít nhất 3 đồ thị/bảng | Sáu thí nghiệm PNG/PDF + CSV | Chọn kết quả phù hợp và phân tích có kiểm chứng |
| Báo cáo 15–20 trang theo giả định trên | Dữ liệu, hình, RESULTS.md, tài liệu khoa học | Biên soạn báo cáo cuối; kho mã không tự tạo báo cáo Word/PDF 15–20 trang |
| Source code có README | Kho mã và hướng dẫn này | Kiểm thử bản bàn giao trên môi trường sạch |
| Slide 10–12 phút; demo 3–5 phút | docs/DEMO.md | Tạo slide, chia vai và diễn tập |
| ≥5 references, trong đó ≥2 bài journal/conference | docs/REFERENCES.bib có 5 nguồn, gồm 4 bài khoa học | Trích đúng chỗ, kiểm tra định dạng và tránh dùng ngày biên dịch PDF làm năm công bố |

Rubric trong ảnh: Theory 20%; Security understanding 20%; Simulation 30%; Analysis 20%; Presentation/code quality 10%. Nên dành thời gian phân tích sai lệch, giả định và khả năng tái lập tương xứng với việc viết mã.

Gợi ý phân bổ báo cáo 18 trang: mở đầu/phạm vi 1; cơ sở lý thuyết 3; giao thức và an toàn 3; mô hình/phương pháp 3; kết quả/phân tích 5; hạn chế và kết luận 1; tài liệu tham khảo 2. Không cần đưa toàn bộ source vào phần chính.

## 7. Những kết luận cần tránh

- “QBER thấp chứng minh không có Eve”: QBER chỉ ràng buộc điều có thể suy ra trong mô hình; nhiễu và tấn công đều có thể góp vào lỗi.
- “Có một lỗi là phát hiện Eve”: đó chỉ là phát hiện sai khác Alice–Bob trong mẫu.
- “Dưới 11% là an toàn, trên 11% là bị nghe lén”: 11% thuộc một bound tiệm cận với giả định cụ thể, không phải bộ phân loại tác nhân gây lỗi.
- “Không thể sao chép nên tuyệt đối an toàn”: no-cloning là nền tảng trực giác, không thay cho chứng minh an toàn toàn hệ thống.
- “Sifted key là secret key”: các bước hậu xử lý còn thiếu và thông tin đã công bố phải được tính đến.
- “Khoảng Wilson 95% là finite-key QKD security”: đó là khoảng thống kê giảng dạy; không cho mức an toàn mật mã composable.
- “Seed cố định sinh khóa bí mật”: seed cố định và NumPy RNG phục vụ tái lập, không dùng để tạo khóa thực.

## 8. Tài liệu và cấu trúc hỗ trợ

- [SCIENCE.md](docs/SCIENCE.md): mô hình, dẫn xuất, giới hạn và cách đọc bài báo.
- [DEMO.md](docs/DEMO.md): kịch bản trình bày, demo và câu hỏi bảo vệ.
- [REFERENCES.bib](docs/REFERENCES.bib): BB84 gốc, Shor–Preskill, review Scarani, Cai–Scarani và IBM Quantum.
- [BB84_tutorial.ipynb](notebooks/BB84_tutorial.ipynb): bài thực hành từng bước.

Tài liệu IBM hiện dùng: [Quantum key distribution](https://quantum.cloud.ibm.com/learning/en/modules/computer-science/quantum-key-distribution). Các hướng dẫn Qiskit cũ có thể dùng API khác; dùng lệnh `qiskit-check` của dự án và lưu phiên bản đã chạy thành công.

## 9. Đọc mã theo thứ tự nào?

| Tệp | Nội dung cần đọc |
|---|---|
| `bb84/core.py` | `BB84Config` kiểm tra tham số; `simulate` thực hiện luồng BB84; `BB84Result` tính các thống kê |
| `bb84/theory.py` | Đường QBER kỳ vọng, tỷ lệ sifted, entropy, Wilson và xác suất thấy lỗi |
| `bb84/experiments.py` | Thiết kế sáu thí nghiệm, chạy lặp, xuất dữ liệu và hình |
| `bb84/__main__.py` | Điểm vào lệnh `python -m bb84`; xem trợ giúp để biết tham số |
| `bb84/report.py`, `bb84/report_style.css` | Xuất báo cáo HTML ngoại tuyến và Markdown, kèm cấu hình/phiên bản/mã băm nguồn |
| `bb84/qiskit_demo.py` | Tám tổ hợp chuẩn bị/đo một qubit, dùng AerSimulator cục bộ |
| `tests/` | Kiểm tra quy tắc phép đo, thống kê kỳ vọng, seed, sifting và các trường hợp biên |

Trong `core.py`, cơ sở `0=Z`, `1=X`; bit `0/1` chọn trạng thái trong cơ sở đó. Biểu diễn gọn này cho đúng xác suất của bốn trạng thái, phép đo Z/X và nhiễu Pauli được mô phỏng; không biểu diễn trạng thái lượng tử tùy ý. Mảng `sift_mask` chỉ chọn vị trí được phát hiện và trùng cơ sở; `test_mask` và `key_mask` chia hai phần rời nhau. Tên `key_mask` là viết tắt cho phần ứng viên chưa công bố, không chứng nhận khóa bí mật.

## 10. Xử lý các lỗi thường gặp trên Windows

| Hiện tượng | Cách xử lý |
|---|---|
| `py` không được nhận diện, hoặc `No installed Pythons found` | Cài Python từ [python.org](https://www.python.org/downloads/windows/), rồi mở PowerShell mới. Kiểm tra `py --version`; nếu Python đã có dưới lệnh `python`, dùng `python -m venv .venv` |
| `No module named bb84` | Chuyển về thư mục chứa README và thư mục `bb84`, không chạy lệnh từ `notebooks` hoặc `results` |
| `No module named numpy/matplotlib` | Cài đúng môi trường: `.\.venv\Scripts\python.exe -m pip install -r requirements.txt` |
| `Activate.ps1 cannot be loaded` | Gọi trực tiếp `.\.venv\Scripts\python.exe` như README; không cần kích hoạt hay đổi Execution Policy |
| Notebook dùng sai Python hoặc thiếu package | Kiểm tra dòng `Python:` ở ô đầu; khởi động Jupyter bằng `.\.venv\Scripts\python.exe -m jupyterlab` và chọn lại kernel |
| Qiskit không có hoặc không chạy | Cài `requirements-optional.txt` trong cùng `.venv`; phần NumPy và sáu thí nghiệm vẫn dùng `requirements.txt` |
| CSV mở trong Excel thành một cột | Dùng Data → From Text/CSV, chọn dấu phẩy và UTF-8; dấu chấm là phân cách thập phân trong tệp |
| HTML thiếu hình khi gửi cho người khác | Gửi cả thư mục kết quả; HTML tham chiếu các PNG bên cạnh, không chỉ gửi riêng `report.html` |
| Lần chạy khác cho vài số khác nhau | Đối chiếu seed, cấu hình, phiên bản NumPy và mã nguồn; xu hướng lý thuyết mới là tiêu chí, không ép mọi lần QBER bằng đúng 25% |

Bộ mã kèm `requirements-tested.txt` ghi đúng phiên bản các phụ thuộc lõi đã dùng để kiểm chứng dưới Python 3.12.14. Muốn đối chiếu số liệu với cùng bộ thư viện:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-tested.txt
```

Trong một môi trường sạch chỉ dành cho dự án, có thể ghi thêm cấu hình đầy đủ để bàn giao:

```powershell
.\.venv\Scripts\python.exe -m pip freeze > requirements-lock.txt
```

Tệp lock chỉ ghi lại môi trường đang dùng; hãy lưu cùng `metadata.json` và kiểm tra cài/chạy trên máy nhóm thứ hai trước khi nộp.


## 11. Kết quả bàn giao đã kiểm tra

- [Bản xác nhận kiểm chứng](docs/VALIDATION.md): lệnh đã chạy, môi trường, kết quả và giới hạn.
- [Kết quả standard](results-standard/RESULTS.md): phân tích từ dữ liệu thực sự đã chạy.
- `results-standard/report.html`: mở bằng trình duyệt trên máy để xem sáu hình và liên kết CSV.
- `results-demo/`: JSON ba tình huống minh họa và kết quả kiểm tra Qiskit.
- CSV chứa seed số nguyên dài: khi nhập Excel, chọn cột `seed` dạng **Text** để tránh làm tròn số. Ô CSV trống là giá trị không xác định, không phải 0.
- Chạy lại vào cùng thư mục sẽ ghi đè các tệp đầu ra của chương trình; nếu không bật `--trace`, chương trình bỏ tệp trace cũ để tránh ghép nhầm phiên.
- Hình 3 dùng trung bình ± một độ lệch chuẩn. Thanh ở cỡ mẫu nhỏ có thể đi xuống dưới 0; đó là cách biểu diễn độ phân tán, không phải QBER thực nghiệm âm hoặc một khoảng xác suất.
