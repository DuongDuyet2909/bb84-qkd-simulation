# Kiểm chứng bản bàn giao

Bản mã 1.0.0 được kiểm tra trong workspace Windows với Python 3.12.14, NumPy 2.3.5, Matplotlib 3.11.2; phần tùy chọn Qiskit 2.5.2 và Qiskit Aer 0.17.2. Các gói lõi và phụ thuộc được ghi trong `requirements-tested.txt`; từng bộ kết quả ghi phiên bản và SHA-256 mã nguồn trong `metadata.json`.

## Những việc đã chạy thực tế

- `python -X utf8 -m unittest discover -s tests -v`: **59 tests, tất cả đạt**. Gồm 26 kiểm tra giao thức/Qiskit, 13 lý thuyết, 8 thí nghiệm, 9 CLI và 3 báo cáo. Log đầy đủ được đưa vào gói ZIP trong `validation/test-results.txt`.
- `python -m bb84 experiments --preset quick --output results-quick --seed 84`: sáu thí nghiệm, 7.253 giây tính toán ở lần kiểm tra; dùng số đo thực tế trong metadata khi cần trích dẫn.
- `python -m bb84 experiments --preset standard --output results-standard --seed 84`: sáu thí nghiệm, **21.760 giây** tính toán ở lần kiểm tra. Các tác vụ khác có thể chạy song song; thời gian không phải benchmark kiểm soát hoặc cam kết cho máy khác.
- `RUN_DEMO.cmd`: chạy thành công ba tình huống và xuất JSON.
- Notebook đã được `nbformat.validate` và thực thi bằng `nbclient` với kernel Python của `.venv`: 8 ô code không lỗi, sinh 2 hình inline. Đã kiểm tra hình.
- Phần Qiskit đã thực thi cả 8 tổ hợp chuẩn bị/đo với 4096 shots. Cùng cơ sở cho đúng bit; khác cơ sở cho kết quả gần 50/50 trong dao động lấy mẫu.
- Đã xem trực tiếp cả sáu PNG thí nghiệm: nhãn, chú thích và đồ thị không bị cắt. HTML được kiểm tra cấu trúc, escaping và liên kết tài nguyên bằng test; chưa kiểm tra bố cục bằng trình duyệt vì công cụ trình duyệt chặn URL tệp cục bộ.

## Một số số liệu standard

| Điều kiện | Kết quả mô phỏng | Lý thuyết |
|---|---:|---:|
| Eve chặn toàn bộ, không nhiễu | QBER mẫu trung bình 24.8601% | 25% |
| Depolarizing p=0.20, không Eve | QBER mẫu trung bình 10.019% | 10% |
| Readout flip p=0.20, không Eve | QBER mẫu trung bình 20.062% | 20% |
| Q=2.5%, m=20 | Xác suất thấy lỗi 39.55% | 39.73% |

Các số này là Monte Carlo với seed/config cố định, không phải phép đo trên phần cứng QKD. Không cần hoặc không nên ép kết quả bằng đúng đường lý thuyết.

## Phạm vi kiểm chứng

Các tests có kiểm tra độc lập quy tắc Born, ghép lỗi, loại bit công bố, mất tín hiệu, bảo toàn số đếm, replay seed, Wilson với số nguyên NumPy và trường hợp thiếu dữ liệu. Đã sửa lỗi tràn số nguyên NumPy trong phép tính Wilson và lỗi giữ trace cũ khi ghi đè một phiên không yêu cầu trace.

Môi trường `.venv` tại máy phát triển kế thừa một phần runtime Codex; **chưa tuyên bố đã kiểm tra cài mới trên máy thứ hai**. Gói ZIP không mang `.venv`; trên máy khác tạo môi trường mới theo README. JupyterLab chưa cài trong môi trường chạy kiểm chứng; notebook được thực thi bằng nbclient. Muốn dùng giao diện JupyterLab, cài `requirements-optional.txt`.

Đây là kiểm chứng tính đúng của mô hình và chương trình trong phạm vi đã nêu, không phải chứng nhận an toàn mật mã. Chưa cài đặt xác thực, sửa lỗi/xác minh khóa, khuếch đại riêng tư hoặc định lý an toàn hữu hạn composable.
