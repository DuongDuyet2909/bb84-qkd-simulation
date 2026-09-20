# Kịch bản demo và thuyết trình

## Chuẩn bị trước buổi bảo vệ

- Chạy tests và preset `quick`, sau đó chạy `standard` để chốt hình cho báo cáo.
- Lưu mã, CSV, hình, `metadata.json`, `RESULTS.md` và `report.html` cùng phiên bản bàn giao.
- Kiểm tra mở `report.html` và notebook trên đúng máy trình bày. Không phụ thuộc internet cho phần chính.
- Đưa vào slide một bảng giả định: qubit lý tưởng, Eve intercept–resend, nhiễu/mất độc lập, chưa triển khai xác thực/EC/PA.
- Cài Qiskit trước nếu muốn dùng; đây là phần tùy chọn, không nên chiếm thời gian của ba kết quả cốt lõi.
- Chuẩn bị hình/HTML đã sinh làm dự phòng nếu thời gian tính toán tại lớp thay đổi. Phân biệt rõ kết quả lưu sẵn và lần chạy trực tiếp.

Trong PowerShell, đứng tại thư mục dự án. Các lệnh sau dùng môi trường đã cài theo README.

## Demo 3–5 phút

| Thời gian | Thao tác | Điều cần nói |
|---|---|---|
| 0:00–0:30 | Nêu Alice, Bob, Eve và mục tiêu | Phân phối khóa; không phải truyền bản rõ trên qubit |
| 0:30–1:20 | Chạy trace chuỗi 16 bit | Đúng/sai cơ sở, sifting, mất tín hiệu nếu có; 16 bit quá ít để kết luận an toàn |
| 1:20–2:10 | Chạy ba tình huống với 10.000 tín hiệu | Không Eve/lý tưởng bằng 0 lỗi; nhiễu tạo lỗi; Eve toàn phần gần 25% trong điều kiện đã nêu |
| 2:10–3:30 | Mở HTML và chọn 3 đồ thị | Eve–QBER, ảnh hưởng cỡ mẫu và loss–retention; so với lý thuyết, giải thích độ dao động |
| 3:30–4:15 | Mở đồ thị tỷ lệ tiệm cận | 11% thuộc bound cụ thể; hình không phải số bit bí mật đã trích xuất |
| 4:15–5:00 | Nêu giới hạn và cách tái lập | Seed/metadata; xác thực, EC/PA và security proof chưa được triển khai |

```powershell
.\.venv\Scripts\python.exe -m bb84 demo --seed 84 --signals 16 --trace
.\.venv\Scripts\python.exe -m bb84 demo --seed 84 --signals 10000
```

Sau hai lệnh, mở `results/report.html` đã chuẩn bị. Không bắt buộc chạy toàn bộ preset standard trực tiếp trong 3–5 phút.

Nếu còn thời gian hoặc giảng viên yêu cầu mạch một qubit:

```powershell
.\.venv\Scripts\python.exe -m bb84 qiskit-check --shots 4096 --seed 84
```

Nêu rõ đây là kiểm tra xác suất mạch trên simulator. Khi khác cơ sở, 4.096 shots cho tỷ lệ gần 50/50; không yêu cầu đúng 2.048 lần mỗi kết quả.

## Slide 10–12 phút

Ảnh đề bài ghi slide 10–12 phút và demo 3–5 phút riêng. Kế hoạch dưới đây xem đó là hai phần thời gian riêng; nếu thời lượng tổng bao gồm demo, giảng viên cần chốt lại và nhóm rút gọn slide.

| Slide | Nội dung | Thời lượng gợi ý |
|---|---|---:|
| 1 | Vấn đề, câu hỏi nghiên cứu, phạm vi | 0:45 |
| 2 | Bốn trạng thái, cơ sở Z/X và xác suất đo | 1:15 |
| 3 | Luồng BB84 và các loại độ dài dữ liệu | 1:00 |
| 4 | Eve intercept–resend; tự suy ra (Q=f/4) | 1:15 |
| 5 | Mô hình nhiễu/mất; phương pháp Monte Carlo | 1:00 |
| 6 | Kết quả Eve–QBER và đường lý thuyết | 1:00 |
| 7 | Cỡ mẫu, xác suất thấy lỗi và giới hạn nhận diện Eve | 1:15 |
| 8 | Mất tín hiệu, chuẩn hóa số bit giữ lại | 0:45 |
| 9 | Bound tiệm cận, 11%, finite-key chưa triển khai | 1:15 |
| 10 | Kết luận có điều kiện; đóng góp nhóm; hướng mở rộng | 0:45 |

Tổng khoảng 10 phút 15 giây, chừa thời gian chuyển người hoặc làm rõ một hình. Đặt nguồn ở slide dùng kết quả của bài báo; để đầy đủ bibliographic entries trong slide cuối hoặc phụ lục.

## Câu hỏi bảo vệ nên chuẩn bị

| Câu hỏi | Ý chính cần trả lời |
|---|---|
| BB84 tạo khóa hay mã hóa thông điệp? | Tạo/phân phối khóa; muốn bảo vệ thông điệp còn cần cơ chế sử dụng khóa |
| Tại sao công bố cơ sở không làm lộ toàn bộ bit? | Cơ sở không chứa giá trị bit; Eve cần đã tương tác với tín hiệu và chịu ràng buộc đo; kết luận bảo mật đầy đủ còn cần proof và hậu xử lý |
| Tại sao Eve gây 25%, không phải 50%? | Sai cơ sở 1/2 nhân xác suất bit sai khi Bob đo lại 1/2, trên các vị trí đã sift |
| Có lỗi có chắc có Eve không? | Không; nhiễu và lỗi thiết bị cũng tạo QBER |
| 0 lỗi trong 16 bit có chứng minh không nghe lén không? | Không; cỡ mẫu nhỏ có thể bỏ sót lỗi và khoảng bất định rộng |
| 11% có phải ngưỡng mọi hệ thống BB84 không? | Không; đó là điểm bound tiệm cận với các giả định cụ thể về nguồn, lỗi và hậu xử lý |
| Vì sao cùng p mà hai mô hình nhiễu khác nhau? | Depolarizing quy ước rho→(1−p)rho+pI/2 cho Q=p/2; readout flip cho Q=p |
| Mất tín hiệu có tự gây lỗi bit không? | Trong mô hình xóa độc lập này thì không; nó giảm dữ liệu và ảnh hưởng bất định |
| Mẫu công bố có giữ làm khóa không? | Không; phải loại các bit đã công bố |
| QBER toàn bộ và QBER mẫu khác nhau thế nào? | Simulator biết cả hai chuỗi; giao thức thực chỉ công bố mẫu và dùng ước lượng thống kê |
| `continue_postprocessing` có phải khóa an toàn không? | Không; còn EC, kiểm tra khóa, PA, xác thực và bound an toàn thích hợp |
| Mô phỏng cổ điển vì sao đủ? | Các phép chuẩn bị/đo một qubit độc lập có xác suất tường minh; không cần máy tính lượng tử để mô phỏng mô hình này |
| Làm sao tái lập? | Cùng mã, môi trường, tham số, seed; đối chiếu metadata và CSV; không chỉ lưu screenshot |

## Gói nộp đề xuất

1. Báo cáo theo số trang giảng viên đã thống nhất; dự kiến 15–20 trang theo dòng yêu cầu bắt buộc trong ảnh.
2. Source code, README và hướng dẫn cài/chạy; loại bỏ `.venv`, cache và file cài đặt lớn khỏi bản nộp.
3. Kết quả CSV, metadata, ít nhất ba hình/bảng được phân tích; HTML để xem nhanh.
4. Slide 10–12 phút, kịch bản demo 3–5 phút.
5. Tài liệu tham khảo ≥5 nguồn, ≥2 bài journal/conference; dùng REFERENCES.bib và trích đúng nơi sử dụng.

Không ghi “đã hoàn thành triển khai QKD an toàn” vào kết luận. Một kết luận phù hợp là: nhóm đã xây dựng mô phỏng tái lập được và kiểm chứng các quan hệ QBER/lấy mẫu/mất tín hiệu trong mô hình đã nêu, đồng thời nhận diện các điều kiện còn thiếu để tạo khóa bí mật trong triển khai thật.
