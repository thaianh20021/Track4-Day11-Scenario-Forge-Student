MSSV: 202602740

# Lab 11 · Scenario Forge — báo cáo

Mỗi câu: trả lời ngắn, **trích số từ `evidence/`** (ghi tên file và trường, ví dụ `mc.json: crashes = 4`). Grader chạy lại với MSSV của bạn; số không khớp `evidence/` thì mất điểm phần D (RUBRIC), và câu dựa trên số sai khó được điểm đầy đủ. Không cần văn hay: một bảng nhỏ và hai, ba câu giải thích là đủ.

Thị trấn của bạn (`meta.json: _run.town`): B

## 1. Phát lại log có trung thực không? (bước A)

Trích số từ `evidence/replay.json`:
- Số kịch bản bị bỏ vì người lái tự gây va chạm (`dropped_human_crash_logs`): **0** / 400 kịch bản (`n_used = 400`).
- Va chạm khi planner chạy trên log phát lại (`replay.crashes`): **109** va chạm, trong đó:
  - `rear` (bị đâm từ phía sau): **94**
  - `side` (va chạm bên hông): **15**
- Va chạm trong thế giới phản ứng (`reactive.crashes`): **1** va chạm (`side: 1`).
- Số va chạm xảy ra ở cả hai môi trường (`crash_in_both`): **1**.

| Môi trường | Tổng va chạm | front | rear | side |
|---|---|---|---|---|
| Log phát lại (replay) | 109 | 0 | 94 | 15 |
| Thế giới phản ứng (reactive) | 1 | 0 | 0 | 1 |

**Giải thích:**
Phần lớn va chạm của log phát lại là va chạm đuôi (`rear`: 94/109, chiếm 86.2%). Đây là **va chạm giả** do sự thiếu tính tương tác (non-reactive) của log: các xe phía sau (đặc biệt là xe bám đuôi TG) chỉ nhắm mắt bám theo quỹ đạo và vận tốc đã ghi của người lái người thật. Khi planner của xe ta phản ứng thận trọng hơn (phanh sớm hoặc nhường đường), xe phía sau không hề phanh theo mà cứ lao tới dẫn đến đâm vào đuôi xe ta. Trong thế giới phản ứng, xe sau lái theo mô hình IDM biết giảm tốc khi khoảng cách hẹp lại, nên toàn bộ 94 vụ đâm đuôi này hoàn toàn biến mất.

**Ví dụ một kịch bản trong `replay_only`:** Kịch bản **#1** (`scenario: 1`, `contact: rear`, `min_ttc_reactive: 2.50 s`): Trên log phát lại, xe ta chủ động giảm tốc để đảm bảo an toàn, khiến xe bám đuôi TG tông vào đuôi xe ta. Tuy nhiên trong môi trường phản ứng, TG nhận biết khoảng cách và tự động hãm phanh, khoảng thời gian va chạm tối thiểu đạt 2.50 s an toàn và không xảy ra va chạm.

---

## 2. Kịch bản bất khả thi (bước B)

Các luật kiểm tra trong `lab11/feasible.py: is_feasible`:
1. **Gia tốc chuyển làn ngang**: $a_{\text{lat}} = \left(\frac{\pi}{\text{cutDur}}\right)^2 \cdot \frac{3.5}{2} \le \mu g$.
   *Căn cứ vật lý:* Ma sát trượt giữa lốp và mặt đường giới hạn gia tốc chuyển làn ngang tối đa; nếu vượt quá $\mu g$, xe sẽ bị trượt mất lái.
2. **Gia tốc phanh sau nhập làn**: $\text{cutBrake} \le \mu g$.
   *Căn cứ vật lý:* Lực ma sát cực đại giữa lốp và mặt đường $F_{\text{max}} = \mu m g$ chỉ cho phép gia tốc hãm tối đa là $\mu g$; lớn hơn là phi thực tế.
3. **Vận tốc người đi bộ**: $\text{pedV} \le 2.5\text{ m/s}$.
   *Căn cứ vật lý:* Người đi bộ sang đường thông thường đi với vận tốc 1.0–1.8 m/s; vận tốc trên 2.5 m/s (~9 km/h) là chạy nước rút, không phù hợp với hành vi người đi bộ đô thị bình thường.
4. **Vận tốc xe cắt làn**: $0 < \text{cutV} \le 22.0\text{ m/s}$ (~80 km/h).
   *Căn cứ vật lý:* Vận tốc xe trong phố không thể âm/bằng 0 khi nhập làn và không vượt quá giới hạn thiết kế đường phố nội thị.

**Phân tích từ `evidence/hunt.json`:**
- Số kịch bản bất khả thi bị loại bỏ trong các cuộc săn:
  - `bus_bypass`: 4
  - `cut_in`: **7** (nhiều nhất)
  - `crosswalk_block`: 3
  - `rear_ended`: 5
- `cut_in` sinh nhiều kịch bản bất khả thi nhất vì thuật toán CEM tối ưu hóa điểm số nguy hiểm (danger score tỉ lệ nghịch với TTC). Để ép TTC về 0 hoặc âm, CEM liên tục giảm `cutDur` xuống cực nhỏ và tăng `cutBrake` lên cực lớn. Những tham số cực đoan này tạo ra va chạm dễ nhất nhưng lại vi phạm giới hạn bám của lốp đường ($\mu g$).
- Nếu **đếm** các kịch bản này là va chạm, ước lượng xác suất rủi ro của planner sẽ bị **thổi phồng sai lệch** (báo cáo những lỗi va chạm trên các kịch bản mà ngoài đời thực không phương tiện nào thực hiện được).

---

## 3. Monte Carlo cho bạn biết gì (bước C1)

Trích số từ `evidence/mc.json`:
- $n = 3000$ lần chạy tự nhiên.
- Số vụ va chạm: $k = 1$.
- Xác suất ước lượng: $\hat{p} = \frac{1}{3000} \approx 3.33 \times 10^{-4}$.
- Khoảng tin cậy Wilson 95%: $[5.88 \times 10^{-5}, 1.89 \times 10^{-3}]$ (rộng gấp hơn 30 lần từ cận dưới lên cận trên).

**Số lần chạy cần thiết để khoảng tin cậy hẹp lại còn $\pm 20\%$ của $p$:**
Nửa độ rộng khoảng tin cậy $1.96 \sqrt{\frac{p(1-p)}{n}} \le 0.2 p \implies n \ge \frac{1.96^2}{0.04 p} \approx \frac{96.04}{p}$.
Với $p \approx 3.33 \times 10^{-4}$, số lần chạy cần là:
$$n \ge \frac{96.04}{3.33 \times 10^{-4}} \approx \mathbf{288\,120}\text{ lần chạy}$$
(Cần gần 300.000 lần chạy Monte Carlo để đạt độ chuẩn xác $\pm 20\%$).

**Các kiểu thất bại chưa xuất hiện:**
Trong 3.000 lần chạy, các kiểu `cut_in`, `crosswalk_block`, `rear_ended`, `other` đều có $k = 0$.
Con số đúng cần báo **không được phép ghi là 0**, mà phải báo bằng **cận trên quy tắc số 3 (Rule of Three)** hoặc cận trên Wilson:
$$\text{Upper Bound} = \frac{3}{n} = \frac{3}{3000} = \mathbf{1.0 \times 10^{-3}}$$
(Theo `mc.json: per_mode`, cận trên Wilson 95% tương ứng là $1.28 \times 10^{-3}$).

---

## 4. Importance sampling, ESS và độ suy biến (bước C3)

Bảng tổng hợp từ `evidence/estimate.json` ($n = 600$ mỗi kiểu, mixture defensive $\beta = 0.2$):

| Kiểu thất bại | Seed | $p$ | hits | ess | top_share |
|---|---|---|---|---|---|
| **bus_bypass** | 0 | $3.59 \times 10^{-4}$ | 38 | 139.1 | 0.240 |
| | 1 | $1.26 \times 10^{-3}$ | 51 | 131.4 | 0.355 |
| | 2 | $6.94 \times 10^{-4}$ | 48 | 130.1 | 0.239 |
| **crosswalk_block** | 0 | $2.70 \times 10^{-6}$ | 53 | 130.6 | 0.161 |
| | 1 | $1.43 \times 10^{-6}$ | 56 | 123.1 | 0.171 |
| | 2 | $7.51 \times 10^{-6}$ | 50 | 120.7 | 0.454 |
| **cut_in** | 0, 1, 2 | 0.0 (cận: 0.025) | 0 | 119–130 | 0.000 |
| **rear_ended** | 0, 1, 2 | 0.0 (cận: 0.025) | 0 | 105–125 | 0.000 |

- **Sự đồng thuận:**
  - Ba seed của `bus_bypass` dao động quanh $3.59 \times 10^{-4} - 1.26 \times 10^{-3}$, hoàn toàn nằm trong khoảng tin cậy Wilson $[5.88 \times 10^{-5}, 1.89 \times 10^{-3}]$ của Monte Carlo ($3.33 \times 10^{-4}$).
  - `crosswalk_block` có xác suất cỡ $10^{-6}$, giải thích vì sao Monte Carlo 3.000 lần không thể phát hiện ra.
- **Hiện tượng `top_share`:** Cả 3 seed đều có `top_share` $< 0.5$ (cao nhất là seed 2 của crosswalk_block đạt 0.454). Khi `top_share` $> 0.5$, phân phối đề xuất bị suy biến (co quá hẹp), dẫn đến phần lớn giá trị ước lượng bị chi phối bởi trọng số của duy nhất 1 mẫu hiếm, khiến ước lượng thiếu ổn định.
- **So sánh ngân sách:** Để đo được xác suất $10^{-6}$ như `crosswalk_block`, Monte Carlo cần cỡ $10^7$ lần chạy. Với Importance Sampling, chỉ cần ngân sách $n = 600$ (kết hợp săn CEM 8 vòng $\times$ 300 mẫu) đã thu được 50–56 mẫu va chạm với kích thước mẫu hiệu dụng ESS $\approx 120-130$.
- **Phần `other` trong tổng:** Trích từ `mc.json` ($k = 0, n = 3000$, cận trên $1.28 \times 10^{-3}$). Không săn `other` vì đây là tập hợp các va chạm ngẫu nhiên không có hàm mục tiêu nguy hiểm cụ thể để thuật toán CEM tối ưu.

---

## 5. Các kiểu thất bại (bước C2 + 3D)

Hình ảnh minh hoạ được chụp từ trình xem 3D (`viewer/index.html`, chương 9 kéo file `evidence/viewer.json`):

1. **Lách qua xe buýt (`bus_bypass`)**:
   - *Chuỗi sự kiện:* Xe buýt đỗ ở làn E2 che khuất tầm nhìn. Xe C2 từ phía sau lách qua xe buýt để chuyển làn ở tốc độ chậm. Xe ta tiến lên ở làn E1 không quan sát kịp vùng mù sau đuôi xe buýt, dẫn đến va chạm góc đầu xe với C2.
   - *Minh hoạ:* `evidence/shots/bus_bypass.jpg` (hoặc xem chấm đậm trong chương 9).
2. **Chặn lối người đi bộ (`crosswalk_block`)**:
   - *Chuỗi sự kiện:* Người đi bộ P1 bước qua đường sau khi bị xe buýt che khuất. Xe ta phát hiện muộn và phanh khẩn cấp, xe đã dừng hẳn ($v = 0$) nhưng thân xe nằm đè lên vạch qua đường, cản lối di chuyển của người đi bộ.
   - *Minh hoạ:* `evidence/shots/crosswalk_block.jpg`.
3. **Kiểu không tìm thấy:** `cut_in` và `rear_ended` không tìm thấy va chạm trong phân phối tự nhiên khả thi của thị trấn B (mọi kịch bản cắt làn thông thường đều được planner xử lý an toàn nhờ khoảng cách IDM hợp lý). Mức độ tin cậy được bảo chứng qua cận trên `upper_zero_hits = 0.025`.
4. **Tại sao không chạy chung một cuộc săn?** Nếu chỉ chạy một cuộc săn chung, CEM sẽ co cụm (collapse) toàn bộ quần thể về kiểu va chạm dễ tìm nhất (ở đây là `bus_bypass`), bỏ sót hoàn toàn các kiểu va chạm tinh vi hơn như `crosswalk_block`.

---

## 6. Sửa planner (bước E + 3D)

Trích số từ `evidence/fix.json`:
- **Chính sách được chọn:** `{'cutinLat': 3.0}` (mở rộng ngưỡng nhận diện xe lấn làn từ 2.15 m lên 3.0 m).
- **Trên tập TRAIN:**
  - `fail` = $9.17 \times 10^{-7}$, `fail_hi` = $1.48 \times 10^{-6}$.
  - Quãng đường trung bình: 215.5 m (giữ nguyên so với gốc 215.8 m).
  - Kiểu chưa thấy trên TRAIN (`unseen`): `['bus_bypass']`.
- **Trên tập TEST:**
  - Bản sửa (`chosen`):
    - `fail` = **$5.94 \times 10^{-6}$** (giảm gần 400 lần so với gốc).
    - `fail_hi_seen` = $1.45 \times 10^{-5}$.
    - `fail_hi` (cận trên hợp lệ): **$3.88 \times 10^{-2}$** (do cộng cận bảo thủ $\frac{3}{0.2 \times 400} = 0.0375$ của kiểu `bus_bypass` vốn là unseen).
    - Quãng đường: 214.2 m, số lần phanh gắt (`harsh`): 8.04 frames.
  - Chính sách gốc (`baseline`):
    - `fail` = **$2.43 \times 10^{-3}$**, `fail_hi_seen` = $5.43 \times 10^{-3}$, `fail_hi` = $6.71 \times 10^{-3}$.
    - Quãng đường: 214.3 m, số lần phanh gắt (`harsh`): 8.52 frames.

**Vì sao `fail_hi` của bản sửa lớn hơn của policy gốc dù bản sửa an toàn hơn?**
Trên TEST, bản sửa triệt tiêu hoàn toàn va chạm `bus_bypass` (0 hits $\implies$ unseen). Theo nguyên tắc chứng nhận xác suất, 0 vụ va chạm trên mẫu hữu hạn $n = 400$ chỉ chứng minh được cận trên cỡ $\frac{15}{n} \approx 0.0375$. Do đó `fail_hi` bắt buộc phải cộng thêm lượng phạt bảo thủ này. Muốn chứng nhận cận trên $< 10^{-3}$ cần tới hơn 15.000 lượt kiểm thử.

**Núm chỉnh "nghe an toàn" nhưng phản tác dụng:**
Ví dụ `cautionV: 5.0` (giảm tốc độ qua chỗ khuất xuống 5 m/s): Khi xe ta phanh quá chậm, quãng đường giảm mạnh xuống 172.8 m (mất > 20%), và tạo ra xung đột với các phương tiện phía sau. Tương tự, nếu tăng `pedBuffer` quá lớn, xe sẽ dừng đột ngột từ rất xa làm tăng rủi ro bị đâm đuôi từ xe TG.

---

## 7. Từ mô phỏng ra đường thật

Ba giả định phân phối tự nhiên trong `space.py` ảnh hưởng nhiều nhất:
1. **Khoảng chấp nhận của xe chuyển làn (`cutGap`)**:
   - *Dữ liệu thật thay thế:* Dữ liệu quỹ đạo camera flycam tại các nút giao đô thị (nguồn: HighD / Argoverse 2 Trajectory dataset).
   - *Hướng sai lệch:* Nếu giả định khe hở của tài xế rộng hơn thực tế, mô phỏng sẽ đánh giá thấp nguy cơ va chạm cắt làn.
2. **Xác suất người đi bộ ngó nhìn qua đầu xe buýt (`pedLook`)**:
   - *Dữ liệu thật thay thế:* Nghiên cứu hành vi người đi bộ qua camera quan sát ngã tư (nguồn: PIE Dataset - Pedestrian Intent Estimation).
   - *Hướng sai lệch:* Nếu tỉ lệ người quan sát thực tế thấp hơn giả định (nhiều người cắm mặt vào điện thoại), va chạm `crosswalk_block` và đâm va người ngoài đời sẽ cao hơn nhiều.
3. **Hệ số ma sát đường ướt ($\mu = 0.5$ vs $\mu = 0.8$)**:
   - *Dữ liệu thật thay thế:* Thống kê khí tượng thủy văn số ngày mưa và đo đạc hệ số ma sát mặt đường nhựa địa phương.
   - *Hướng sai lệch:* Nếu đường thực tế có ổ gà/dầu loang làm $\mu < 0.5$, quãng đường phanh thực tế dài hơn khiến số vụ va chạm vượt xa con số trong mô phỏng.

---

## 8. Giới hạn

Ba điều mà xác suất báo cáo **không** phản ánh:
1. **Môi trường chỉ có một con phố thẳng cố định:** Không có ngã tư chữ thập, bùng binh, xe máy luồn lách hay các hành vi đi ngược chiều.
2. **Mô hình tài xế IDM lý tưởng hóa:** Các xe khác luôn tuân thủ vật lý và IDM, không có hành vi tài xế say xỉn, mất tập trung hoặc cố tình tạt đầu hung hăng.
3. **Cảm biến hình học hoàn hảo:** Ngoại trừ bóng che của xe buýt, cảm biến nhận diện được tọa độ và vận tốc của mọi đối tượng với độ trễ bằng 0 và không có nhiễu (noise/dropout) do thời tiết xấu.

*Nếu có thêm một tuần:* Tôi sẽ mở rộng kiểm thử với mô hình cảm biến có độ trễ/nhiễu đo lường, bổ sung các tác nhân xe máy hai bánh đặc trưng đô thị và tích hợp kịch bản mặt đường biến đổi ma sát liên tục.

---

## 9. Rắc rối của bạn (bước G + chương 10)

- **Rắc rối:** Xe đạp ở làn bên cạnh (E2) bất ngờ lạng tay lái sang trái $1.8 - 2.3\text{ m}$ lấn vào làn E1 của xe ta để tránh chướng ngại vật/cửa xe mở bên lề đường, khi xe ta đang áp sát cách $10 - 16\text{ m}$.
- **Căn cứ:** Xe đạp di chuyển chậm ($v = 5\text{ m/s}$) nhưng lạng nhanh trong 2 giây. Xe ta đang chạy $12.5\text{ m/s}$ trong làn E1; hành lang kiểm soát mặc định của planner hẹp (`cutinLat = 2.15`), dẫn đến phát hiện xe đạp trễ khi xe đạp đã lấn sâu vào làn.
- **Giả định (`hazard.json`):**
  - `space`: `{"h0_x": [45.0, 80.0], "h0_swerve": [1.8, 2.3], "h0_trig": [10.0, 16.0]}`.
  - `exposure`: $0.03$ (tần suất ~3 lần trong 100 chuyến đi nội thành đông đúc có làn hỗn hợp).
  - `why`: Tránh chướng ngại vật đột ngột; gia tốc ngang tối đa $\approx 2.8\text{ m/s}^2 \le 3.0\text{ m/s}^2$ đảm bảo tính khả thi cơ học.
- **Kết quả theo `evidence/mine.json`** (1.487 kịch bản khả thi trên 1.500 mẫu, tỉ lệ chấp nhận `accepted` = **99.1%**):
  - **Chính sách gốc (baseline):**
    - Tổng va chạm: **202** (trong đó **202** vụ tránh được nếu phanh hết cỡ ngay khi thấy - `avoidable`, 0 `unavoidable`, 0 `unattributed`, 23 vụ ở vận tốc thấp `< 1 m/s`).
    - $P(\text{lỗi planner} \mid \text{hazard}) = \mathbf{1.36 \times 10^{-1}}$ (Wilson: $[1.19 \times 10^{-1}, 1.54 \times 10^{-1}]$).
    - Tần suất mỗi chuyến: **$4.08 \times 10^{-3}$** (cận trên $4.63 \times 10^{-3}$).
  - **Chính sách đã sửa (chosen: `cutinLat = 3.0`):**
    - Tổng va chạm: **77** vụ (giảm gần 3 lần so với gốc!), toàn bộ **77** vụ là `avoidable`.
    - $P(\text{lỗi planner} \mid \text{hazard}) = \mathbf{5.18 \times 10^{-2}}$ (Wilson: $[4.16 \times 10^{-2}, 6.42 \times 10^{-2}]$).
    - Tần suất mỗi chuyến: **$1.55 \times 10^{-3}$** (cận trên $1.93 \times 10^{-3}$).
- **Hình ảnh:** Chụp từ chương 10 khi xe đạp lạng ra và xe ta đạp phanh dừng tại `evidence/shots/hazard_bike.jpg`.
- **Người tự lái:** Khi tự lái trong chương 10, người lái phát hiện cử động thân người và đầu xe đạp chớm nghiêng từ sớm nên chủ động rà phanh hoặc hơi lách nhẹ sang mép trái, tránh được hoàn toàn va chạm mà không cần phanh khẩn cấp dúi dụi.
- **Cách sửa:** Núm chỉnh `cutinLat = 3.0` đã giúp giảm va chạm từ 202 xuống 77 vụ nhờ mở rộng biên quét sang làn bên cạnh. Tuy nhiên để tránh triệt để, planner cần bổ sung **logic dự đoán hướng quỹ đạo (trajectory projection)** dựa trên góc lái của phương tiện hai bánh thay vì chỉ đo vị trí ngang hiện tại.
