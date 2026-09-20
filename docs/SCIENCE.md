# Mô hình khoa học và giới hạn kết luận

## 1. Phạm vi của project

BB84 là giao thức **phân phối khóa**, không trực tiếp mã hóa một thông điệp. Sau khi có khóa phù hợp, người dùng còn cần một hệ mật và cơ chế bảo vệ thông điệp. QKD không loại bỏ yêu cầu xác thực danh tính/kênh cổ điển. Nếu không xác thực, Eve có thể giả mạo hai bên qua tấn công người trung gian.

Dự án này mô phỏng xác suất đo của tín hiệu một qubit độc lập, với Alice/Bob lý tưởng, Eve intercept–resend, mô hình nhiễu được khai báo và mất tín hiệu độc lập. Máy tính cổ điển có thể mô phỏng hiệu quả mô hình này vì không cần lưu trạng thái rối của một hệ nhiều qubit. NumPy đã đủ để khảo sát Monte Carlo; Qiskit bổ sung cách nhìn qua cổng lượng tử.

Các giả định chính:

1. Bit và lựa chọn cơ sở của Alice/Bob độc lập theo phân phối đã cấu hình. Trong mô phỏng, RNG giả ngẫu nhiên được dùng để tái lập.
2. Bốn trạng thái BB84 là lý tưởng; không có rò rỉ từ quá trình chuẩn bị/đo hay các kênh phụ.
3. Eve được mô hình hóa bằng một tấn công cụ thể: chặn–đo với cơ sở chọn đều–gửi lại. Đây không phải mọi tấn công individual, collective hoặc coherent.
4. Mất tín hiệu được mô hình hóa bằng xóa độc lập, không phụ thuộc bit, cơ sở hay thông tin Eve.
5. Nhiễu được lấy độc lập theo từng tín hiệu theo một trong hai mô hình ở dưới.
6. Xác thực và hậu xử lý cổ điển được thảo luận về mặt giao thức nhưng chưa triển khai.

Vì vậy, kiểm thử đúng mô phỏng chứng minh mã phù hợp đặc tả đã chọn; nó không chứng minh BB84 an toàn trước mọi kẻ tấn công hay chứng nhận thiết bị QKD.

## 2. Bốn trạng thái và phép đo

\[
|+\rangle=(|0\rangle+|1\rangle)/\sqrt{2},\qquad
|-\rangle=(|0\rangle-|1\rangle)/\sqrt{2}.
\]

Alice chuẩn bị \(|0\rangle,|1\rangle\) nếu chọn cơ sở \(Z\), hoặc \(|+\rangle,|-\rangle\) nếu chọn \(X\). Bob đo trong \(Z\) hoặc \(X\). Trong kênh lý tưởng:

- Trùng cơ sở: kết quả bằng bit Alice với xác suất 1.
- Khác cơ sở: mỗi kết quả xuất hiện với xác suất 1/2, độc lập với bit Alice.

Trong mạch Qiskit khởi tạo \(|0\rangle\), dùng cổng \(X\) nếu bit bằng 1 rồi \(H\) nếu cơ sở chuẩn bị là \(X\). Để đo theo cơ sở \(X\), đặt \(H\) trước phép đo theo cơ sở tính toán. Thứ tự này quan trọng: \(HX|0\rangle=|-\rangle\), còn \(XH|0\rangle=|+\rangle\).

## 3. Chuỗi xử lý và ký hiệu

```text
Phát tín hiệu → mất/nhiễu/tấn công → Bob đo → sifting
→ chọn mẫu ngẫu nhiên và công bố bit mẫu → ước lượng QBER
→ quyết định giảng dạy → [EC + kiểm tra khóa + PA: chưa triển khai]
```

Các thông điệp cổ điển trong giao thức thật phải được xác thực; bước này không được thể hiện bằng một thao tác mạng trong chương trình.

| Ký hiệu | Đơn vị/ý nghĩa |
|---|---|
| \(N_{\rm sent}\) | Số tín hiệu Alice phát |
| \(N_{\rm detected}\) | Số tín hiệu còn sau mất tín hiệu |
| \(N_{\rm sift}\) | Số kết quả có cơ sở Alice/Bob trùng nhau và không mất |
| \(m\) | Số bit được lấy ra công bố để ước lượng lỗi |
| \(n=N_{\rm sift}-m\) | Số bit còn lại trước sửa lỗi và privacy amplification |
| \(k\) | Số lỗi trong mẫu \(m\) bit |
| \(\widehat Q=k/m\) | QBER quan sát trong mẫu; không xác định khi \(m=0\) |
| \(Q_{\rm full}\) | QBER trên toàn bộ sifted data; chỉ bộ mô phỏng có để kiểm chứng |
| \(\ell\) | Độ dài khóa bí mật sau hậu xử lý đầy đủ; chương trình này chưa tạo \(\ell\) |

Không đánh đồng \(N_{\rm sent}\), \(N_{\rm sift}\), \(n\) hoặc gọi tất cả là “key length”. Khi vẽ tỷ lệ, mẫu số phải xuất hiện trong nhãn trục/chú thích.

Với xác suất chọn \(Z\) là \(p_Z\) giống nhau ở Alice/Bob và xác suất mất độc lập \(L\):

\[
\mathbb E[N_{\rm sift}]/N_{\rm sent}
=(1-L)\left[p_Z^2+(1-p_Z)^2\right].
\]

Với \(p_Z=1/2\), không mất tín hiệu, tỷ lệ này bằng \(1/2\). Đây là kỳ vọng, không buộc mỗi lần chạy phải đúng một nửa. Mã giữ dữ liệu trùng cơ sở ở cả \(Z\) và \(X\); nếu chuyển sang BB84 bất đối xứng chỉ \(ZZ\) tạo khóa, phải sửa phần chuẩn hóa và sử dụng dữ liệu \(XX\) để ước lượng lỗi pha phù hợp.

## 4. Intercept–resend và QBER 25%

Xét một bit đã qua sifting trong kênh không nhiễu. Nếu Eve chặn:

1. Eve chọn sai cơ sở so với Alice với xác suất \(1/2\).
2. Sau phép đo sai cơ sở, Bob đo lại theo cơ sở Alice cho bit sai với xác suất \(1/2\).

Vì vậy \(P(\text{lỗi}\mid\text{bị chặn, sifted})=1/4\). Nếu mỗi tín hiệu bị chặn với xác suất \(f\), thì

\[
Q_E=f/4.
\]

Mốc 25% là QBER kỳ vọng trong mô hình **chặn toàn bộ, chọn cơ sở Eve đều, thiết bị lý tưởng, không nhiễu khác**. QBER đo được dao động quanh mốc đó. Không thấy lỗi trong mẫu ngắn vẫn có thể xảy ra khi có Eve. Mức lỗi cũng không trực tiếp bằng số bit Eve biết trong khóa cuối vì khóa cuối còn phụ thuộc sửa lỗi, thông tin công bố và privacy amplification.

## 5. Hai mô hình nhiễu khác nhau

### Depolarizing

Quy ước của dự án là

\[
\rho\mapsto (1-p)\rho+p I/2.
\]

Với xác suất \(p\), trạng thái được thay bằng trạng thái trộn tối đa. Khi đo đúng cơ sở, trạng thái này cho bit sai với xác suất \(1/2\), nên không có Eve thì \(Q=p/2\). Đây không phải quy ước “chọn ngẫu nhiên một trong ba lỗi Pauli với tổng xác suất \(p\)”; quy ước đó cho hệ số khác. Luôn ghi công thức kênh cùng tên `depolarizing`.

Khi kết hợp Eve theo mô hình trên:

\[
Q=(1-p)\frac f4+\frac p2.
\]

### Readout flip

Sau phép đo Bob, bit kết quả bị đảo với xác suất \(p\). Khi không có Eve, \(Q=p\). Hai lỗi đảo liên tiếp có thể triệt tiêu nhau, nên với Eve:

\[
Q=\frac f4(1-p)+\left(1-\frac f4\right)p
=\frac f4+p-\frac{fp}{2}.
\]

Không cộng thẳng \(Q_E+p\), và không so sánh hai đường theo cùng tham số \(p\) như thể hai kênh gây cùng QBER. Nếu cần so sánh ở cùng mức lỗi nền \(q_0\), dùng \(p=2q_0\) cho depolarizing và \(p=q_0\) cho readout flip trong miền hợp lệ.

Mất tín hiệu độc lập không tự đảo bit. Trong mô hình này nó giảm số bit thu được và làm khoảng ước lượng rộng hơn vì có ít dữ liệu; thiết bị thực có dark counts, bất đối xứng detector và các hiệu ứng khác chưa được mô phỏng.

## 6. Lấy mẫu, khoảng Wilson và quyết định giảng dạy

Mẫu được chọn ngẫu nhiên từ sifted data; các bit đã công bố bị loại khỏi phần còn lại. Với \(m>0\), chương trình có thể tính khoảng Wilson hai phía mức tin cậy \(c\). Đặt \(z=\Phi^{-1}((1+c)/2)\), \(\widehat Q=k/m\):

\[
C=\frac{\widehat Q+z^2/(2m)}{1+z^2/m},\qquad
W=\frac{z}{1+z^2/m}
\sqrt{\frac{\widehat Q(1-\widehat Q)}m+\frac{z^2}{4m^2}}.
\]

Khoảng được viết \([C-W,C+W]\), giới hạn trong \([0,1]\). Với \(c=0.95\), dùng cận trên của khoảng này cho minh họa quyết định. **Cận trên khoảng hai phía 95% không phải cùng quy ước với cận một phía 95%.** Wilson là khoảng gần đúng cho tỷ lệ nhị thức, không phải bảo đảm bao phủ đúng trong mọi trường hợp.

- `continue_postprocessing`: dữ liệu đủ và cận trên thỏa điều kiện ngưỡng minh họa.
- `abort`: không đạt điều kiện ngưỡng minh họa.
- `insufficient_data`: thiếu dữ liệu để thực hiện quyết định như đặc tả.

Phải đọc trạng thái cùng cỡ mẫu. Ví dụ, 0 lỗi trên mẫu rất ngắn không có nghĩa QBER thực bằng 0. Với lấy mẫu không hoàn lại và điều kiện tổng số lỗi cố định, phân phối phù hợp là siêu bội; khoảng Wilson ở đây không phải cận finite-key chứng minh an toàn cho phần dữ liệu chưa công bố.

Trong mô hình lỗi i.i.d. với xác suất \(Q\), xác suất mẫu \(m\) bit có **ít nhất một lỗi** là

\[
P_{\ge 1}=1-(1-Q)^m.
\]

Đây là tiêu chí khác với “cận trên Wilson vượt ngưỡng”. Không gán công thức này cho xác suất `abort`. Khi không có nhiễu và chỉ có Eve, thay \(Q=f/4\). Khi có nhiễu, thấy lỗi không chỉ ra được nguồn lỗi. Với đúng \(K\) lỗi trong \(S\) bit và lấy mẫu không hoàn lại, xác suất chính xác có ít nhất một lỗi là \(1-\binom{S-K}{m}/\binom{S}{m}\).

## 7. Bound tiệm cận và ý nghĩa mốc 11%

Đặt entropy nhị phân

\[
h_2(q)=-q\log_2q-(1-q)\log_2(1-q),
\]

với \(h_2(0)=h_2(1)=0\). Với BB84 qubit/nguồn đơn photon lý tưởng, khóa dài vô hạn, xử lý cổ điển một chiều không noisy preprocessing và sửa lỗi đạt giới hạn Shannon, một tỷ lệ khóa bí mật đạt được trên mỗi bit khóa thô dùng tạo khóa là

\[
r_\infty=\left[1-h_2(e_Z)-h_2(e_X)\right]_+.
\]

Ở đây khóa được xét trong \(Z\); lỗi \(X\) ràng buộc lỗi pha của khóa đó. Với giả định đối xứng \(e_Z=e_X=Q\), biểu thức trở thành \([1-2h_2(Q)]_+\), về 0 ở \(Q\approx0.1100\). Với hiệu suất sửa lỗi tham chiếu \(f_{EC}\ge1\):

\[
r_\infty^{\rm ref}=\left[1-h_2(Q)-f_{EC}h_2(Q)\right]_+.
\]

Các đồ thị của project chỉ dùng miền \(0\le Q\le 0.5\) cho diễn giải nhiễu/lỗi thông thường. Không dùng tính đối xứng của entropy để diễn giải tùy tiện một QBER gần 1 như thể cùng pipeline có thể tạo khóa.

Cần nêu rõ:

- Đây là tỷ lệ tham chiếu lý thuyết, không phải khóa đã tạo từ một lần chạy. Ngưỡng quyết định 0,11 và mức confidence 0,95 trong demo không tạo thành một định lý an toàn.
- Sửa lỗi kém hơn, khối hữu hạn hoặc mô hình nguồn/thiết bị khác có thể giảm lượng khóa. Các biến thể hậu xử lý khác có thể có ngưỡng khác; 11% không phải giới hạn tuyệt đối của mọi BB84.
- Hai cơ sở có QBER khác nhau phải được xử lý phù hợp; không tự thay tất cả bằng QBER gộp rồi kết luận an toàn.
- Chuyển từ tỷ lệ trên mỗi bit khóa thô sang trên mỗi tín hiệu phát cần tính phát hiện, sifting, mẫu kiểm tra và các chi phí khác. Không nhân/trừ sifting hai lần.
- An toàn còn đòi hỏi xác thực kênh cổ điển, nguồn ngẫu nhiên thích hợp, thiết bị đáp ứng mô hình, accounting thông tin rò rỉ, EC verification và privacy amplification.

Nguồn: [Shor–Preskill (2000)](https://doi.org/10.1103/PhysRevLett.85.441); [Scarani và cộng sự (2009), Appendix A](https://doi.org/10.1103/RevModPhys.81.1301).

## 8. Finite-key: phần mở rộng nên trình bày thế nào?

Trong một thí nghiệm hữu hạn, QBER quan sát có bất định. Một phân tích an toàn hữu hạn phải chọn cận thống kê phù hợp cho đại lượng quyết định an toàn, tính lượng rò rỉ khi sửa lỗi/kiểm tra, chọn quy trình privacy amplification và phân bổ tham số an toàn theo định lý áp dụng. Khóa cuối có thể ngắn hơn nhiều so với tính bằng bound tiệm cận, thậm chí không có khóa dương.

Project này **chưa triển khai** một finite-key composable security proof. Đồ thị cỡ mẫu giúp thấy bất định thống kê, là bước chuẩn bị để hiểu finite-key. Không ghi “khóa an toàn với xác suất 95%” từ khoảng Wilson; mức tin cậy thống kê đó khác tham số an toàn mật mã của một định lý.

Nếu mở rộng, chọn một biến thể giao thức và một theorem cụ thể, liệt kê giả định, định nghĩa từng epsilon, tính đủ leakage, xác thực, correctness và secrecy. Phải tách phần đã chứng minh với xấp xỉ/suy diễn số. Bài [Cai–Scarani (2009)](https://doi.org/10.1088/1367-2630/11/4/045024) cung cấp một cách tiếp cận lịch sử; phần decoy-state trong chính bài này dùng xử lý dao động thống kê đơn giản hóa, nên không gán cho mọi công thức một bảo đảm tổng quát hơn tác giả công bố.

### Khác nhau về ký hiệu giữa bài báo

| Nguồn | Định nghĩa cần nhớ |
|---|---|
| Scarani review, §II.B.4 | Secret fraction \(r=\lim\ell/n\); \(n\) là raw key; \(R\) trong \(K=Rr\) là raw-key rate, đã chứa sifting |
| Cai–Scarani, §2 | \(N\) là số tín hiệu phát hiện trước sifting, \(n=Np_Z^2\), \(m=Np_X^2\), \(r=\ell/N\); \(R\) là detection rate |
| Project này | Dùng tên rõ như tín hiệu phát, detected, sifted, sample và remaining; không đồng nhất các mẫu số |

Cai–Scarani xét biến thể bất đối xứng: \(ZZ\) tạo khóa, \(XX\) ước lượng Eve. Không bê nguyên hệ số \(p_Z^2\) sang một mô phỏng giữ cả \(ZZ\) và \(XX\) làm dữ liệu mà không giải thích.

## 9. Lộ trình đọc bốn PDF người dùng cung cấp

Số trang dưới đây theo bản PDF đã gửi, không phải số trang tạp chí.

| Tài liệu | Đọc trước | Đọc mở rộng |
|---|---|---|
| Bennett–Brassard, *Quantum Cryptography: Public Key Distribution and Coin Tossing* (1984) | Phần phân phối khóa; bốn trạng thái và ví dụ Alice/Bob/Eve | Coin tossing nằm ngoài phạm vi mô phỏng BB84 của project |
| Shor–Preskill (2000) | Trang 1; Protocol 3 và đoạn 11% ở trang 4 | CSS và chuỗi quy đổi chứng minh trang 1–3; không cần tự tái tạo toàn bộ proof để hoàn thành bài mô phỏng |
| Scarani và cộng sự (2009) | I.B trang 3–5; II.B–C trang 8–11 | III.B trang 21–26; Appendix A trang 44–45; finite-key ở VIII.A.1 trang 41 |
| Cai–Scarani (2009) | §2.1–2.3 trang 2–5 | §3 nguồn coherent yếu/decoy; §4 entanglement-based nếu chọn hướng nâng cao |

**Năm công bố:** Shor–Preskill là 2000; review Scarani là 2009; Cai–Scarani là 2009. Các PDF có ngày in/biên dịch lại 2024 hoặc 2018 không làm thay đổi năm xuất bản. Những câu “hiện chưa có chứng minh...” hoặc “state of the art” trong bài cũ mô tả bối cảnh khi bài được viết, không mặc nhiên mô tả hiện tại.

## 10. Checklist phân tích kết quả

1. Đường mô phỏng có phù hợp đường kỳ vọng trong khoảng dao động Monte Carlo không?
2. Nếu có sai lệch: do nhầm mẫu số, tham số kênh, cỡ mẫu nhỏ, sai số RNG hay lỗi mã?
3. Thanh sai số là độ lệch chuẩn giữa các lần chạy, sai số của trung bình hay khoảng tin cậy? Chú thích phải đúng loại đang dùng.
4. Cùng seed, cấu hình, phiên bản và mã có tạo lại kết quả không? Đổi seed có giữ xu hướng không?
5. Có tách QBER toàn bộ mà simulator biết khỏi QBER mẫu mà giao thức có thể công bố không?
6. Kết luận có nhắc mô hình Eve, nguồn/thiết bị lý tưởng và EC/PA còn thiếu không?
7. Đồ thị finite-sample có bị gọi quá mức thành security proof hoặc khả năng nhận diện Eve không?

Giới hạn cần trình bày trong báo cáo là một phần của kết quả khoa học, không chỉ là ghi chú cuối trang.
