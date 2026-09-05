# -*- coding: utf-8 -*-
"""
Module Cognitive Blindspot Diagnostic (Chẩn Đoán Điểm Mù Nhận Thức 6 Chiều).
Đo lường năng lực tư duy, vạch trần các bẫy nhận thức tiềm ẩn và cá nhân hóa lộ trình 3-6 tháng:
1. First Principles (Bản chất vs Bắt chước)
2. Bayesian Updating (Xác suất khách quan vs Cố chấp)
3. Inversion (Nghịch đảo & Antifragile vs Quá lạc quan)
4. Second-Order Thinking (Tầm nhìn lan tỏa vs Cái lợi trước mắt)
5. Optionality & Asymmetry (Vị thế lồi vs Rủi ro đối xứng)
6. Empirical Falsification (Kiểm chứng khả bác vs Thiên kiến xác nhận)
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Any, Optional

from utils.knowledge import load_user_history, save_user_history

# -----------------------------------------------------------------------------
# 1. ĐỊNH NGHĨA 6 CHIỀU NHẬN THỨC
# -----------------------------------------------------------------------------
COGNITIVE_DIMENSIONS: Dict[str, Dict[str, str]] = {
    "first_principles": {
        "name": "Tư Duy Nguyên Bản (First Principles)",
        "icon": "🔬",
        "description": "Khả năng phân rã vấn đề về chân lý bất biến đo lường được, không tư duy bằng sự bắt chước đám đông.",
    },
    "bayesian": {
        "name": "Xác Suất & Cập Nhật Bayes",
        "icon": "🎲",
        "description": "Nhìn thế giới theo phổ xác suất, không định kiến, luôn cập nhật niềm tin khi có dữ liệu mới.",
    },
    "inversion": {
        "name": "Tư Duy Đảo Ngược (Inversion)",
        "icon": "⚠️",
        "description": "Tìm cách phòng tránh những sai lầm ngu ngốc chắc chắn xảy ra thay vì ảo tưởng kế hoạch hoàn hảo.",
    },
    "second_order": {
        "name": "Tư Duy Bậc Hai & Hệ Thống",
        "icon": "🌊",
        "description": "Luôn tự hỏi 'Và sau đó điều gì sẽ xảy ra tiếp theo?' để nhìn thấy chuỗi phản ứng dây chuyền dài hạn.",
    },
    "optionality": {
        "name": "Tùy Chọn & Bất Đối Xứng Lồi",
        "icon": "🛡️",
        "description": "Thiết kế vị thế giới hạn tổn thất nhỏ nhất nhưng để ngỏ tiềm năng sinh lời vô hạn khi biến động xảy ra.",
    },
    "falsification": {
        "name": "Kiểm Chứng Khả Bác (Popper)",
        "icon": "💥",
        "description": "Chủ động tìm kiếm bằng chứng chứng minh mình sai, không rơi vào bẫy tự huyễn hoặc và thiên kiến xác nhận.",
    },
}

# -----------------------------------------------------------------------------
# 2. NGÂN HÀNG 12 CÂU HỎI TÌNH HUỐNG BẪY SÂU SẮC
# -----------------------------------------------------------------------------
DIAGNOSTIC_QUESTIONS: List[Dict[str, Any]] = [
    # --- DIMENSION 1: FIRST PRINCIPLES ---
    {
        "id": "DIAG-01",
        "dimension": "first_principles",
        "title": "Bẫy Phép Loại Suy (Reasoning by Analogy)",
        "scenario": (
            "Bạn muốn khởi nghiệp hoặc thực hiện một dự án học tập mới. Mọi người trong ngành khuyên: "
            "'Chi phí tiêu chuẩn trên thị trường hiện nay là 100 triệu vì tất cả các công ty đi trước đều chi như vậy'. Bạn sẽ làm gì?"
        ),
        "options": [
            {
                "text": "Bóc tách cấu trúc chi phí thành các nguyên vật liệu, giờ công và năng lượng cơ bản nhất để tự tính giá vốn lý thuyết từ số 0.",
                "score": 100,
                "label": "Elite First Principles",
            },
            {
                "text": "Tìm 3 đối tác rẻ hơn để thương lượng giảm giá 15-20% so với giá thị trường hiện tại.",
                "score": 60,
                "label": "Tối ưu hóa gia tăng",
            },
            {
                "text": "Chấp nhận mức giá 100 triệu vì tin rằng thị trường đã được định giá hiệu quả bởi những người đi trước.",
                "score": 20,
                "label": "Bắt chước thụ động",
            },
            {
                "text": "Vay thêm tiền để chi tiêu vượt trội hơn các đối thủ nhằm tạo ấn tượng hoành tráng.",
                "score": 0,
                "label": "Bẫy sĩ diện & Lãng phí",
            },
        ],
        "trap": "Bẫy bắt chước: Đám đông coi quy ước hiện tại là chân lý vật lý.",
    },
    {
        "id": "DIAG-02",
        "dimension": "first_principles",
        "title": "Tách Rời Sự Thật vs Ý Kiến",
        "scenario": (
            "Trong một buổi họp, một chuyên gia có uy tín lớn khẳng định: 'Thị trường/Kỳ thi này chắc chắn sẽ diễn ra theo hướng X, ai cũng thấy điều đó'. Đa số mọi người gật đầu tán thành. Bạn phản ứng ra sao?"
        ),
        "options": [
            {
                "text": "Lịch sự yêu cầu xem các số liệu đo lường thô độc lập làm nền tảng cho nhận định, tách riêng dữ liệu thực tế khỏi suy diễn cá nhân của chuyên gia.",
                "score": 100,
                "label": "Elite First Principles",
            },
            {
                "text": "Lên mạng tìm kiếm xem các chuyên gia khác có ý kiến tương tự không.",
                "score": 50,
                "label": "Kiểm chứng xã hội",
            },
            {
                "text": "Tin tưởng hoàn toàn vì người nói là chuyên gia đầu ngành có nhiều năm kinh nghiệm.",
                "score": 10,
                "label": "Bẫy sùng bái uy quyền (Authority Bias)",
            },
            {
                "text": "Lập tức bác bỏ và làm ngược lại hoàn toàn để chứng tỏ mình khác biệt.",
                "score": 20,
                "label": "Nghịch lý phản kháng cảm tính",
            },
        ],
        "trap": "Bẫy uy quyền: Nhầm lẫn danh tiếng của một người với tính đúng đắn của dữ liệu.",
    },

    # --- DIMENSION 2: BAYESIAN UPDATING ---
    {
        "id": "DIAG-03",
        "dimension": "bayesian",
        "title": "Cập Nhật Niềm Tin Khi Dữ Liệu Thay Đổi",
        "scenario": (
            "Bạn vừa phân tích rất kỹ và tin tưởng 90% rằng cổ phiếu A (hoặc dự án B) sẽ thành công lớn. Tuy nhiên, tuần này có 2 dữ liệu tài chính mới công bố cho thấy các giả định cốt lõi của bạn đã sai lệch 30%. Bạn sẽ làm gì?"
        ),
        "options": [
            {
                "text": "Lập tức hạ xác suất thành công xuống và chủ động cắt giảm tỷ trọng hoặc tái cấu trúc dự án mà không để cái tôi chi phối.",
                "score": 100,
                "label": "Cập nhật Bayesian",
            },
            {
                "text": "Tạm dừng theo dõi trong 1 tháng để xem tình hình có tự hồi phục không.",
                "score": 40,
                "label": "Trì hoãn né tránh",
            },
            {
                "text": "Tìm kiếm các bài phân tích khác trên mạng để tìm bằng chứng chứng minh 2 dữ liệu xấu kia chỉ là tạm thời.",
                "score": 10,
                "label": "Bẫy thiên kiến xác nhận",
            },
            {
                "text": "Tăng gấp đôi vốn đầu tư để chứng minh niềm tin ban đầu của mình là đúng.",
                "score": 0,
                "label": "Bẫy gỡ gạc cảm tính (Gambler's Fallacy)",
            },
        ],
        "trap": "Bẫy tự ái trí tuệ: Coi việc thay đổi nhận định là thừa nhận thất bại.",
    },
    {
        "id": "DIAG-04",
        "dimension": "bayesian",
        "title": "Bỏ Quên Tỷ Lệ Nền (Base Rate Fallacy)",
        "scenario": (
            "Một người bạn kể với bạn về một mô hình khởi nghiệp quán cà phê độc lạ và khẳng định chắc chắn 99% sẽ kiếm tiền tỷ vì ý tưởng chưa ai làm. Tỷ lệ đóng cửa của các quán cà phê mới mở trong 2 năm đầu là 85%. Bạn đánh giá thế nào?"
        ),
        "options": [
            {
                "text": "Lấy tỷ lệ sống sót chung 15% làm điểm xuất phát (Prior), rồi mới xem xét các lợi thế cụ thể xem có đủ kéo xác suất lên trên 30% hay không.",
                "score": 100,
                "label": "Tư duy Bayesian & Base Rate",
            },
            {
                "text": "Tin rằng nếu ý tưởng thực sự độc lạ và đam mê thì xác suất thành công phải là 70-80%.",
                "score": 30,
                "label": "Ảo tưởng cá nhân",
            },
            {
                "text": "Hoàn toàn gạt bỏ ý tưởng vì cho rằng tỷ lệ chết 85% thì không ai nên mở quán cà phê nữa.",
                "score": 40,
                "label": "Quá bi quan",
            },
            {
                "text": "Đầu tư tiền ngay vì sợ người khác cướp mất ý tưởng độc quyền.",
                "score": 0,
                "label": "Bẫy FOMO mù quáng",
            },
        ],
        "trap": "Bỏ quên tỷ lệ nền: Đánh giá cơ hội dựa trên câu chuyện truyền cảm hứng thay vì xác suất thực tế.",
    },

    # --- DIMENSION 3: INVERSION ---
    {
        "id": "DIAG-05",
        "dimension": "inversion",
        "title": "Lập Kế Hoạch Bằng Cách Nghịch Đảo (Invert, Always Invert)",
        "scenario": (
            "Bạn chuẩn bị dẫn dắt một dự án quan trọng trong 6 tháng tới. Đa phần các quản lý sẽ tập trung vẽ ra viễn cảnh thành công rực rỡ. Bước đi đầu tiên của bạn là gì?"
        ),
        "options": [
            {
                "text": "Tổ chức một buổi 'Tiền khám nghiệm' (Pre-mortem): Đặt giả định dự án đã thất bại thảm hại sau 6 tháng, truy vết nguyên nhân và bịt kín các lỗ hổng chết người ngay hôm nay.",
                "score": 100,
                "label": "Tư duy Đảo ngược Charlie Munger",
            },
            {
                "text": "Lập biểu đồ Gantt chi tiết từng ngày và động viên toàn đội ngũ giữ tinh thần tích cực 100%.",
                "score": 50,
                "label": "Quản lý truyền thống",
            },
            {
                "text": "Tập trung tìm kiếm các phần thưởng lớn để tạo động lực cho các thành viên.",
                "score": 30,
                "label": "Động lực bề nổi",
            },
            {
                "text": "Không cần lo xa, việc gì đến sẽ giải quyết sau để tránh tinh thần bi quan.",
                "score": 0,
                "label": "Lạc quan tếu & Bất cẩn",
            },
        ],
        "trap": "Bẫy lạc quan độc hại: Coi việc lường trước thất bại là suy nghĩ tiêu cực.",
    },
    {
        "id": "DIAG-06",
        "dimension": "inversion",
        "title": "Bảo Toàn Sự Sống Còn (Survival First)",
        "scenario": (
            "Trong một thương vụ hoặc trò chơi mạo hiểm có 99% cơ hội thắng 10 tỷ đồng, nhưng có 1% rủi ro bạn sẽ phá sản hoàn toàn hoặc mất tự do cá nhân. Bạn sẽ ra quyết định thế nào?"
        ),
        "options": [
            {
                "text": "Tuyệt đối từ chối. Không bao giờ đánh đổi một điều bạn cần cho một điều bạn chỉ muốn, khi rủi ro tổn thất là sự diệt vong (Ruin risk).",
                "score": 100,
                "label": "Nguyên lý Chống Diệt Vong Munger/Buffett",
            },
            {
                "text": "Chấp nhận chơi vì tỷ lệ thắng 99% là quá áp đảo về mặt kỳ vọng toán học.",
                "score": 10,
                "label": "Bẫy kỳ vọng mù quáng",
            },
            {
                "text": "Cố gắng rủ thêm bạn bè cùng gánh 1% rủi ro đó.",
                "score": 30,
                "label": "Chuyển giao rủi ro vô trách nhiệm",
            },
            {
                "text": "Cầu nguyện may mắn vì 1% xác suất là rất nhỏ.",
                "score": 0,
                "label": "Mê tín & Đánh bạc",
            },
        ],
        "trap": "Bẫy rủi ro diệt vong: Toán học kỳ vọng chỉ đúng trong trò chơi lặp vô hạn, nhưng một lần 'game over' sẽ xóa sổ bạn vĩnh viễn.",
    },

    # --- DIMENSION 4: SECOND-ORDER THINKING ---
    {
        "id": "DIAG-07",
        "dimension": "second_order",
        "title": "Nhận Diện Chuỗi Phản Ứng Dây Chuyền",
        "scenario": (
            "Một thành phố quyết định áp giá trần tiền thuê nhà để giúp người thu nhập thấp có chỗ ở rẻ hơn. Kết quả Bậc 1: Người đang thuê nhà được trả ít tiền hơn ngay tháng tới. Điều gì sẽ diễn ra ở Bậc 2 và Bậc 3?"
        ),
        "options": [
            {
                "text": "Chủ nhà ngừng bảo trì, ngừng xây mới phòng trọ vì lợi nhuận teo tóp ➔ Nguồn cung sụp đổ ➔ Người nghèo đến sau hoàn toàn không tìm được chỗ ở và phố ổ chuột hình thành.",
                "score": 100,
                "label": "Tư duy Bậc hai sắc bén",
            },
            {
                "text": "Mọi người nghèo đều sẽ có nhà ở ổn định và kinh tế thành phố sẽ phát triển thịnh vượng.",
                "score": 10,
                "label": "Tư duy Bậc một ngây thơ",
            },
            {
                "text": "Chủ nhà sẽ vui vẻ chấp nhận giảm lợi nhuận vì tinh thần vì cộng đồng.",
                "score": 0,
                "label": "Ảo tưởng đạo đức",
            },
            {
                "text": "Chính phủ sẽ phải bỏ tiền xây toàn bộ nhà trọ cho cả thành phố.",
                "score": 40,
                "label": "Suy luận phi thực tế",
            },
        ],
        "trap": "Bẫy tư duy Bậc một: Chỉ nhìn vào tác động trước mắt mà mù tịt trước phản ứng đối trọng của hệ thống.",
    },
    {
        "id": "DIAG-08",
        "dimension": "second_order",
        "title": "Và Sau Đó Điều Gì Sẽ Xảy Ra? (And Then What?)",
        "scenario": (
            "Để giải quyết áp lực doanh số trong tuần này, một giám đốc kinh doanh quyết định giảm giá 40% sản phẩm cao cấp. Kết quả Bậc 1: Doanh số tuần này tăng vọt kỷ lục. Hệ quả dài hạn là gì?"
        ),
        "options": [
            {
                "text": "Hình ảnh thương hiệu cao cấp bị phá hủy vĩnh viễn, khách hàng hình thành thói quen chờ giảm giá mới mua, và biên lợi nhuận ròng các tháng sau lao dốc.",
                "score": 100,
                "label": "Tư duy Bậc hai & Định vị thương hiệu",
            },
            {
                "text": "Công ty sẽ tiếp tục giảm giá mỗi tuần để duy trì đà tăng trưởng doanh số này.",
                "score": 20,
                "label": "Vòng xoáy tự sát",
            },
            {
                "text": "Khách hàng sẽ biết ơn công ty và trung thành mua hàng với giá gốc sau đó.",
                "score": 10,
                "label": "Ảo tưởng khách hàng",
            },
            {
                "text": "Đối thủ sẽ sợ hãi và tự động rút lui khỏi thị trường.",
                "score": 0,
                "label": "Ảo tưởng độc quyền",
            },
        ],
        "trap": "Ăn thịt tương lai: Đổi lấy chiến thắng ngắn hạn bằng cái chết dài hạn.",
    },

    # --- DIMENSION 5: OPTIONALITY & ASYMMETRY ---
    {
        "id": "DIAG-09",
        "dimension": "optionality",
        "title": "Thiết Kế Vị Thế Quả Tạ (Barbell Strategy)",
        "scenario": (
            "Bạn có 100 triệu tiền tiết kiệm và muốn bắt đầu tích lũy tài sản cho tương lai. Chiến lược nào phản ánh tư duy Bất đối xứng lồi (Convex Asymmetry) của Nassim Taleb?"
        ),
        "options": [
            {
                "text": "Giữ 85-90 triệu ở nơi cực kỳ an toàn (tiết kiệm, tài sản phòng thủ); 10-15 triệu đầu tư vào các cơ hội có tiềm năng tăng trưởng phi tuyến $10x-50x$ hoặc học kỹ năng đòn bẩy cao.",
                "score": 100,
                "label": "Chiến lược Quả tạ (Barbell)",
            },
            {
                "text": "Bỏ toàn bộ 100 triệu vào các tài sản rủi ro vừa phải có mức sinh lời trung bình 10-12%/năm.",
                "score": 50,
                "label": "Vị thế trung gian rủi ro ngầm",
            },
            {
                "text": "All-in 100 triệu vào một đồng coin hoặc cổ phiếu đầu cơ nóng theo lời khuyên hội nhóm.",
                "score": 0,
                "label": "Đánh bạc hủy diệt",
            },
            {
                "text": "Giữ 100 triệu trong két sắt không đầu tư gì vì sợ mất tiền.",
                "score": 30,
                "label": "Bị lạm phát ăn mòn",
            },
        ],
        "trap": "Bẫy lưng chừng: Đứng ở khoảng giữa không an toàn tuyệt đối mà cũng không hứng được cơ hội đột phá phi tuyến.",
    },
    {
        "id": "DIAG-10",
        "dimension": "optionality",
        "title": "Đòn Bẩy Của Sự Lựa Chọn (Preserving Optionality)",
        "scenario": (
            "Bạn là học sinh/sinh viên hoặc người bắt đầu sự nghiệp. Bạn đứng trước 2 lời mời: Công việc A trả lương cao ngay nhưng kỹ năng rất hẹp và đóng băng cơ hội; Công việc B lương vừa phải nhưng cho bạn tự do học Code, AI, kết nối mạng lưới tinh hoa và giữ quyền chọn mở. Bạn chọn gì?"
        ),
        "options": [
            {
                "text": "Chọn B: Giai đoạn đầu đời ưu tiên tối đa hóa Quyền chọn (Optionality) và đường cong học tập hơn là tối đa hóa thu nhập ngắn hạn.",
                "score": 100,
                "label": "Tư duy Quyền chọn mở",
            },
            {
                "text": "Chọn A: Tiền hôm nay là chắc chắn nhất, tương lai tính sau.",
                "score": 30,
                "label": "Chiết khấu tương lai quá đà",
            },
            {
                "text": "Không chọn bên nào vì sợ cam kết trách nhiệm.",
                "score": 0,
                "label": "Tê liệt nhận thức",
            },
            {
                "text": "Chọn A và dùng tiền lương cao đó để thuê người khác học hộ mình.",
                "score": 20,
                "label": "Ảo tưởng thuê ngoài trí tuệ",
            },
        ],
        "trap": "Bẫy lồng vàng: Bị khóa chặt vào mức lương ngắn hạn mà đánh mất toàn bộ tương lai cấp số nhân.",
    },

    # --- DIMENSION 6: EMPIRICAL FALSIFICATION ---
    {
        "id": "DIAG-11",
        "dimension": "falsification",
        "title": "Tiêu Chuẩn Bác Bỏ Của Karl Popper",
        "scenario": (
            "Bạn xây dựng một lý thuyết hoặc chiến lược đầu tư/học tập và tự tin rằng nó hoàn hảo. Làm thế nào để chứng minh chiến lược này có giá trị khoa học thực sự?"
        ),
        "options": [
            {
                "text": "Chỉ rõ ra chính xác điều kiện biên hoặc bằng chứng thực nghiệm cụ thể nào NẾU XUẤT HIỆN sẽ chứng minh là bạn ĐANG SAI (Falsification Criteria).",
                "score": 100,
                "label": "Tiêu chuẩn khả bác Karl Popper",
            },
            {
                "text": "Tìm kiếm thêm 100 ví dụ trong lịch sử khớp hoàn hảo với lý thuyết của bạn.",
                "score": 30,
                "label": "Bẫy thiên kiến xác nhận",
            },
            {
                "text": "Giải thích sao cho bất kỳ kết quả nào xảy ra cũng chứng minh là bạn đã đoán trước được.",
                "score": 0,
                "label": "Ngụy khoa học & Ngụy biện",
            },
            {
                "text": "Thách thức những người khác phản biện và nếu họ không bác bỏ được thì nghĩa là bạn đúng.",
                "score": 20,
                "label": "Ngụy biện nại vào sự vô tri",
            },
        ],
        "trap": "Ngụy khoa học: Một lý thuyết không thể bị bác bỏ bởi bất kỳ điều kiện nào là một lý thuyết vô giá trị.",
    },
    {
        "id": "DIAG-12",
        "dimension": "falsification",
        "title": "Chống Bẫy Thiên Kiến Nhận Thức Muộn (Hindsight Bias)",
        "scenario": (
            "Một sự kiện bất ngờ lớn vừa xảy ra trên thị trường hoặc trong xã hội. Rất nhiều người trên mạng lập tức viết bài: 'Tôi đã thấy trước chuyện này từ nhiều tháng trước'. Phản xạ chuẩn của một trí tuệ tinh hoa là gì?"
        ),
        "options": [
            {
                "text": "Bỏ qua các lời tuyên bố suông; chỉ tin vào các dự báo đã được ghi nhận bằng văn bản trước sự kiện kèm tỷ lệ xác suất rõ ràng và có 'Skin in the game'.",
                "score": 100,
                "label": "Chống Thiên kiến nhận thức muộn",
            },
            {
                "text": "Tin tưởng và bấm follow ngay những người tuyên bố đã đoán đúng.",
                "score": 10,
                "label": "Bẫy ngây thơ truyền thông",
            },
            {
                "text": "Cũng tự thuyết phục bản thân rằng thực ra mình cũng đã lờ mờ đoán được điều đó.",
                "score": 0,
                "label": "Tự dối lừa bản thân (Self-deception)",
            },
            {
                "text": "Tranh cãi gay gắt với họ dưới phần bình luận.",
                "score": 20,
                "label": "Tiêu hao năng lượng vô ích",
            },
        ],
        "trap": "Thiên kiến nhận thức muộn: Bộ não viết lại ký ức để tạo ảo tưởng rằng thế giới dễ đoán.",
    },
]


# -----------------------------------------------------------------------------
# 3. BỘ MÁY CHẤM ĐIỂM & TẠO BÁO CÁO RADAR
# -----------------------------------------------------------------------------
def evaluate_diagnostic_submission(answers: Dict[str, int]) -> Dict[str, Any]:
    """
    Tính điểm 6 chiều không gian nhận thức từ danh sách lựa chọn của người học.
    answers: dict mapping question_id -> option_index (0, 1, 2, 3)
    """
    dim_scores: Dict[str, List[int]] = {k: [] for k in COGNITIVE_DIMENSIONS}

    for q in DIAGNOSTIC_QUESTIONS:
        qid = q["id"]
        chosen_idx = answers.get(qid, None)
        if chosen_idx is not None and 0 <= chosen_idx < len(q["options"]):
            score = q["options"][chosen_idx]["score"]
        else:
            score = 0
        dim = q["dimension"]
        dim_scores[dim].append(score)

    dim_percentages: Dict[str, float] = {}
    for dim, scores in dim_scores.items():
        if scores:
            dim_percentages[dim] = round(sum(scores) / len(scores), 1)
        else:
            dim_percentages[dim] = 0.0

    # Tính điểm tổng quan
    overall_index = round(sum(dim_percentages.values()) / len(dim_percentages), 1)

    # Tìm thế mạnh và điểm mù
    sorted_dims = sorted(dim_percentages.items(), key=lambda x: x[1], reverse=True)
    top_strength = sorted_dims[0]
    critical_blindspot = sorted_dims[-1]

    # Xếp hạng danh hiệu tư duy
    if overall_index >= 90:
        rank_title = "Bậc Thầy Nhận Thức Tinh Hoa (Grandmaster)"
        rank_desc = "Khả năng phân rã và phản xạ nhận thức đã tiệm cận mức vô thức. Điểm mù cực thấp."
    elif overall_index >= 75:
        rank_title = "Nhà Chiến Lược Sắc Bén (Elite Strategist)"
        rank_desc = "Tư duy logic và xác suất vượt trội so với đám đông, cần bịt kín các điểm mù nghịch đảo."
    elif overall_index >= 60:
        rank_title = "Người Thực Hành Năng Động (Active Practitioner)"
        rank_desc = "Đã thoát khỏi lối mòn học vẹt cơ bản, nhưng vẫn dễ mắc bẫy thiên kiến khi đối mặt bất định."
    else:
        rank_title = "Tân Binh Khởi Động (Awakening Apprentice)"
        rank_desc = "Bộ não còn chịu nhiều ảnh hưởng của phép bắt chước (Analogy) và bẫy dopamine ngắn hạn."

    # Lộ trình đề xuất 3-6 tháng
    recommendations = []
    if dim_percentages.get("inversion", 0) < 70:
        recommendations.append("Luyện sâu Tab 2 (Chế độ Inversion) & Tab 3 (Mô hình Bẫy đảo ngược): Luôn làm bài tập Pre-mortem trước mọi dự án.")
    if dim_percentages.get("bayesian", 0) < 70:
        recommendations.append("Khắc sâu Tư duy Bayes & Base Rate: Ghi lại xác suất chủ quan vào Tab 7 (Nhật ký quyết định) để theo dõi sai số.")
    if dim_percentages.get("second_order", 0) < 70:
        recommendations.append("Tập thói quen hỏi 'Và sau đó điều gì sẽ xảy ra?' ít nhất 3 nhịp trước mọi quyết định công việc và tài chính.")
    if dim_percentages.get("first_principles", 0) < 70:
        recommendations.append("Rèn luyện thói quen bóc tách Sự thật vs Ý kiến trong Tab 6 (Elite Daily Workout 15 phút).")
    if not recommendations:
        recommendations.append("Duy trì nhịp rèn luyện 15 phút mỗi ngày tại Tab 6 và bắt đầu ghi chép các thương vụ lớn vào Tab 7 Decision Journal.")

    return {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "overall_index": overall_index,
        "rank_title": rank_title,
        "rank_desc": rank_desc,
        "dimension_scores": dim_percentages,
        "top_strength": {
            "dim": top_strength[0],
            "name": COGNITIVE_DIMENSIONS[top_strength[0]]["name"],
            "score": top_strength[1],
        },
        "critical_blindspot": {
            "dim": critical_blindspot[0],
            "name": COGNITIVE_DIMENSIONS[critical_blindspot[0]]["name"],
            "score": critical_blindspot[1],
        },
        "recommendations": recommendations,
    }


def save_user_diagnostic_result(username: str, result: Dict[str, Any]) -> None:
    """Lưu kết quả chẩn đoán vào hồ sơ người dùng."""
    hist = load_user_history(username)
    diag_history = hist.setdefault("diagnostic_history", [])
    diag_history.insert(0, result)
    hist["diagnostic_history"] = diag_history[:10]  # Giữ 10 lần đo gần nhất
    save_user_history(username, hist)


def get_latest_diagnostic_result(username: str) -> Optional[Dict[str, Any]]:
    """Lấy kết quả chẩn đoán gần nhất của người dùng."""
    hist = load_user_history(username)
    diag_history = hist.get("diagnostic_history", [])
    if diag_history:
        return diag_history[0]
    return None
