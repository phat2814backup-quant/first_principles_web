# -*- coding: utf-8 -*-
"""Quiz & Active Recall Engine (Elite Cognitive Mastery System).

Hệ thống luyện nhớ và phản xạ tư duy:
1. Curated Scenario-Based Quizzes for:
   - 9 Chế độ Tư duy Elite
   - 88 Mô hình Hạt nhân (Munger Latticework)
   - 100 Nguyên lý Khởi thủy
2. Spaced Retrieval Flashcard Generator (Active Recall)
3. AI Dynamic Quiz Generator (Gemini Multi-key Failover)
4. AI Feynman Challenge Evaluator
5. User Mastery Stats Tracking
"""

from __future__ import annotations

import json
import random
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Union

import google.generativeai as genai

from utils.knowledge import load_user_history, save_user_history, load_knowledge_base
from utils.mental_models import get_all_models, filter_models

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# =============================================================================
# 0. NGÂN HÀNG TRẮC NGHIỆM LÝ THUYẾT RÀNH MẠCH (THEORY FOUNDATION QUIZ)
# =============================================================================
THEORY_MODES_QUIZ = [
    {
        "id": "TH-MODE-01",
        "concept": "First Principles (Tư duy Nguyên bản)",
        "question": "Theo Aristotle và Elon Musk, bản chất lý thuyết cốt lõi của Tư duy Nguyên bản (First Principles Thinking) là gì?",
        "options": [
            "A. Phân rã bài toán về những chân lý cơ bản nhất không thể suy diễn thêm, tách biệt Sự thật (Fact) khỏi Ý kiến (Opinion) và tái thiết kế giải pháp từ số 0.",
            "B. Tìm giải pháp đơn giản nhất trong số các phương án đang có sẵn trên thị trường.",
            "C. Lập kế hoạch tài chính chi tiết 5 năm dựa trên kết quả của các công ty đi trước.",
            "D. Phân tích điểm mạnh, điểm yếu, cơ hội và thách thức (SWOT) theo thông lệ ngành."
        ],
        "correct_index": 0,
        "explanation": "First Principles là phương pháp tư duy bóc tách tận cùng chân lý bất biến (vật lý, toán học), đối lập hoàn toàn với Reasoning by Analogy (suy luận bắt chước theo kinh nghiệm đám đông).",
        "trap_analysis": "Bẫy bắt chước (Analogy Trap): Tin rằng điều gì người khác đang làm thì mặc định là tối ưu nhất."
    },
    {
        "id": "TH-MODE-02",
        "concept": "Tư duy Xác suất & Cập nhật Bayes (Probabilistic & Bayesian)",
        "question": "Trong tư duy xác suất Bayes, công thức cốt lõi để cập nhật niềm tin khi xuất hiện dữ kiện mới là gì?",
        "options": [
            "A. Posterior (Xác suất mới) ∝ Prior (Niềm tin ban đầu / Tỷ lệ nền) × Likelihood (Khả năng xuất hiện của dữ kiện mới).",
            "B. Posterior = Trung bình cộng của tất cả các ý kiến chuyên gia uy tín trong ngành.",
            "C. Posterior = Niềm tin ban đầu cộng thêm cảm xúc và trực giác nhạy bén của nhà đầu tư.",
            "D. Posterior = 100% nếu có ít nhất một bài báo hoặc nguồn tin nội bộ xác nhận."
        ],
        "correct_index": 0,
        "explanation": "Định lý Bayes ép tư duy không nhìn nhận thế giới theo nhị nguyên Đúng/Sai, mà nhìn theo phổ xác suất liên tục được điều chỉnh khách quan theo dữ kiện thực nghiệm.",
        "trap_analysis": "Bẫy thờ ơ tỷ lệ nền (Base Rate Fallacy) & Bẫy Cố chấp: Quên mất xác suất ban đầu hoặc không chịu hạ xác suất khi dữ kiện thực tế xấu đi."
    },
    {
        "id": "TH-MODE-03",
        "concept": "Tư duy Đảo ngược (Inversion — Charlie Munger)",
        "question": "Quy tắc cốt lõi của phương pháp Tư duy Đảo ngược (Inversion / Premortem) trong việc ra quyết định là gì?",
        "options": [
            "A. Thay vì tìm cách để thành công rực rỡ, hãy liệt kê mọi điều chắc chắn dẫn tới thảm họa/thất bại rồi chủ động né tránh chúng.",
            "B. Luôn làm điều ngược lại với những gì đồng nghiệp hoặc đối thủ đang làm.",
            "C. Bán tháo toàn bộ danh mục tài sản khi thị trường vừa mới xuất hiện một tin tức xấu.",
            "D. Đảo ngược thứ tự các công việc trong ngày từ việc dễ nhất làm trước đến việc khó nhất."
        ],
        "correct_index": 0,
        "explanation": "Charlie Munger đúc kết: 'Người ta thường quá tập trung vào việc làm sao để trở nên xuất chúng, mà quên mất rằng việc bền bỉ tránh những điều ngu ngốc mới tạo ra kết quả phi thường'.",
        "trap_analysis": "Bẫy chỉ nhìn về phía trước (Forward-only): Chỉ vẽ kịch bản màu hồng mà mù tịt trước những lỗ thủng làm chìm tàu."
    },
    {
        "id": "TH-MODE-04",
        "concept": "Tư duy Bậc hai (Second-Order Thinking — Howard Marks)",
        "question": "Điểm phân định cốt lõi giữa Tư duy Bậc một và Tư duy Bậc hai (Second-Order Thinking) là gì?",
        "options": [
            "A. Bậc một chỉ nhìn tác động hiển hiện trước mắt; Bậc hai luôn hỏi 'Và sau đó điều gì xảy ra?' để tính phản ứng của các tác nhân và hệ quả lan truyền 1–3 năm tới.",
            "B. Bậc một là suy nghĩ định tính, Bậc hai là suy nghĩ định lượng bằng máy tính.",
            "C. Bậc một dành cho người mới đi làm, Bậc hai chỉ dành riêng cho các tỷ phú.",
            "D. Bậc hai là suy nghĩ đi suy nghĩ lại hai lần trước khi phát biểu."
        ],
        "correct_index": 0,
        "explanation": "Hầu hết các sai lầm thảm họa xã hội và kinh tế đều bắt nguồn từ tư duy bậc một: làm một việc có vẻ tốt tức thời nhưng hủy hoại cấu trúc hệ thống về lâu dài.",
        "trap_analysis": "Bẫy tầm nhìn ngắn hạn: Coi hệ quả trước mắt là toàn bộ câu chuyện mà không dự phóng phản ứng dây chuyền."
    },
    {
        "id": "TH-MODE-05",
        "concept": "Tư duy Tùy chọn & Bất đối xứng (Optionality & Barbell — Nassim Taleb)",
        "question": "Chiến lược Đòn tạ (Barbell Strategy) của Nassim Nicholas Taleb được cấu trúc lý thuyết như thế nào?",
        "options": [
            "A. 85-90% nguồn lực đặt vào các tài sản an toàn tuyệt đối (tránh rủi ro hủy diệt), 10-15% phân bổ vào các tùy chọn có rủi ro giới hạn nhưng tiềm năng lợi nhuận vô hạn bất đối xứng.",
            "B. Dồn toàn bộ 100% tài sản vào các cơ hội có rủi ro trung bình để sinh lời ổn định quanh năm.",
            "C. Vay nợ tối đa (đòn bẩy cao) khi nhận thấy một cơ hội có vẻ chắc thắng 99%.",
            "D. Chia đều tài sản thành 10 phần bằng nhau và đầu tư dàn trải không phân biệt rủi ro."
        ],
        "correct_index": 0,
        "explanation": "Chiến lược Barbell giúp hệ thống đạt trạng thái Chống Mong Manh (Antifragile): Tuyệt đối không bị xóa sổ khi có thiên nga đen, nhưng luôn có cửa bùng nổ khi cơ hội lớn đến.",
        "trap_analysis": "Bẫy vùng giữa chết chóc (Middle Ground): Chọn vị thế rủi ro trung bình — vừa đủ bấp bênh để mất sạch, nhưng tiềm năng tăng trưởng lại bị chặn trần."
    },
    {
        "id": "TH-MODE-06",
        "concept": "Mạng lưới Đa ngành Latticework (Charlie Munger)",
        "question": "Tại sao Charlie Munger khẳng định việc nắm vững các mô hình hạt nhân từ nhiều ngành khoa học cơ bản là bắt buộc?",
        "options": [
            "A. Để tránh Hội chứng Người cầm búa (Man with a Hammer) và kích hoạt hiệu ứng cộng hưởng Lollapalooza khi các quy luật từ nhiều ngành cùng hội tụ.",
            "B. Để có thể thể hiện sự uyên bác trong các cuộc đàm phán kinh doanh phức tạp.",
            "C. Vì chỉ cần một môn khoa học duy nhất là kinh tế học đã đủ sức giải thích toàn bộ thế giới nếu học đủ sâu.",
            "D. Để không bao giờ cần phải tham khảo ý kiến của các chuyên gia tư vấn."
        ],
        "correct_index": 0,
        "explanation": "Thực tế là một mạng lưới liên kết phức tạp. Người chỉ có một lăng kính duy nhất sẽ luôn bóp méo thực tế để vừa vặn với chuyên môn hạn hẹp của mình.",
        "trap_analysis": "Hội chứng chuyên gia hạn hẹp: Cầm búa thì nhìn đâu cũng thấy đinh."
    },
    {
        "id": "TH-MODE-07",
        "concept": "Thực nghiệm Nhanh (Iterative Lean Thinking)",
        "question": "Vòng lặp học hỏi cốt lõi trong Tư duy Thực nghiệm Nhanh (Build - Measure - Learn) nhằm mục đích giải quyết căn bệnh tư duy nào?",
        "options": [
            "A. Bệnh Phân tích Tê liệt (Analysis Paralysis): Ngồi suy diễn lý thuyết trong phòng kín mà không đưa giả thuyết ra va chạm với thực tế đo lường được.",
            "B. Bệnh thiếu vốn đầu tư mạo hiểm giai đoạn hạt giống.",
            "C. Bệnh không thể xin được giấy phép kinh doanh của cơ quan quản lý.",
            "D. Bệnh tuyển dụng nhân sự quá nhanh so với quy mô doanh thu."
        ],
        "correct_index": 0,
        "explanation": "Trong môi trường bất định cao, mọi kế hoạch trên giấy đều là giả định chưa được chứng minh. Tốc độ thực nghiệm vi mô với chi phí thấp quyết định tốc độ chạm vào sự thật.",
        "trap_analysis": "Bẫy ảo tưởng kế hoạch hoàn hảo: Bỏ hàng năm trời làm sản phẩm mà không chịu tiếp xúc với phản hồi của người dùng."
    },
    {
        "id": "TH-MODE-08",
        "concept": "Lý thuyết Trò chơi & Ma trận Động lực (Game Theory & Incentives)",
        "question": "Quy tắc thiết kế cơ chế (Mechanism Design) trong Lý thuyết Trò chơi đòi hỏi điều gì để tổ chức tự vận hành bền vững?",
        "options": [
            "A. Căn chỉnh động lực (Aligned Incentives) sao cho việc hành động vì lợi ích chung cũng chính là phương án tối đa hóa lợi ích cá nhân của từng tác nhân.",
            "B. Sử dụng camera giám sát dày đặc và các hình phạt tiền nặng nề cho mọi sai sót nhỏ.",
            "C. Kêu gọi tinh thần trách nhiệm và lòng yêu nghề tự nguyện của các thành viên.",
            "D. Thay đổi toàn bộ đội ngũ quản lý sau mỗi quý để tránh việc thông đồng lợi ích."
        ],
        "correct_index": 0,
        "explanation": "Con người phản ứng với động lực (Incentives), không phản ứng với khẩu hiệu. Khi cơ chế win-win được thiết kế chuẩn, sự tự giác xuất hiện mà không cần cưỡng chế.",
        "trap_analysis": "Bẫy ngây thơ: Trông đợi con người hành động vì sự tốt đẹp khi mà cơ chế lương thưởng ngầm lại đang khuyến khích họ gian lận."
    },
    {
        "id": "TH-MODE-09",
        "concept": "Đa quy mô Thời gian (Multi-Scale Time Horizons — Jeff Bezos)",
        "question": "Theo triết lý kinh doanh của Jeff Bezos, đâu là trọng tâm của Tư duy Đa quy mô Thời gian (10-year horizon)?",
        "options": [
            "A. Xác định những nguyên lý và nhu cầu cốt lõi KHÔNG THAY ĐỔI trong 10-20 năm tới để dồn toàn lực đầu tư vào đó, thay vì mải miết chạy theo trào lưu ngắn hạn.",
            "B. Bỏ qua hoàn toàn việc kiếm lợi nhuận và kiểm soát dòng tiền của ngày hôm nay.",
            "C. Thay đổi chiến lược cốt lõi của công ty sau mỗi tháng dựa trên biến động giá cổ phiếu.",
            "D. Thuê các nhà chiêm tinh học để dự báo chính xác nền kinh tế của 2 thập kỷ tới."
        ],
        "correct_index": 0,
        "explanation": "Lợi thế cạnh tranh khổng lồ và sức mạnh lãi kép luôn thuộc về người dám neo giữ tầm nhìn vào những thứ không đổi và kiên định thực thi trong 10 năm.",
        "trap_analysis": "Bẫy thiển cận (Hyperbolic Discounting): Bộ não người luôn muốn dopamine tức thì, định giá quá cao cái lợi hôm nay và xem nhẹ tương lai 10 năm."
    }
]

THEORY_MODELS_QUIZ = [
    {
        "id": "TH-MOD-01",
        "model_id": "PHYS-01",
        "model_name": "Đòn bẩy (Leverage)",
        "pillar": "Vật lý học",
        "tier": 1,
        "question": "Về mặt lý thuyết bản chất, 4 loại đòn bẩy tối thượng của nền kinh tế hiện đại (Naval Ravikant) bao gồm những gì?",
        "options": [
            "A. Lao động (Labor), Vốn (Capital), Mã nguồn (Code) và Nội dung (Media) — trong đó Code và Media có chi phí cận biên bằng 0.",
            "B. Tiền vay ngân hàng, Vay nóng người thân, Bán nhà và Thế chấp tài sản.",
            "C. Nói chuyện hay, Quan hệ ngoại giao tốt, Đi nhậu giỏi và Chăm chỉ làm thêm giờ.",
            "D. Công nghệ thông tin, Bất động sản, Vàng miếng và Tiền điện tử."
        ],
        "correct_index": 0,
        "explanation": "Đòn bẩy không cần sự cho phép (Permissionless leverage) là Code và Media: bạn làm việc một lần, nhưng sản phẩm có thể nhân bản phục vụ hàng triệu người trong lúc bạn ngủ.",
        "trap_analysis": "Bẫy đòn bẩy tài chính thiếu biên độ an toàn: phóng đại lợi nhuận thì cũng phóng đại rủi ro đến mức cháy tài khoản."
    },
    {
        "id": "TH-MOD-02",
        "model_id": "PHYS-03",
        "model_name": "Entropy & Định luật 2 Nhiệt động học",
        "pillar": "Vật lý học",
        "tier": 1,
        "question": "Định luật 2 Nhiệt động học khẳng định điều gì về trạng thái mặc định của mọi hệ thống khép kín?",
        "options": [
            "A. Trong một hệ kín, mức độ hỗn loạn (Entropy) luôn có xu hướng tự nhiên tăng dần theo thời gian nếu không được nạp thêm năng lượng từ bên ngoài.",
            "B. Hệ thống kín sẽ tự động trở nên ngăn nắp và tối ưu hơn theo thời gian nhờ quy luật chọn lọc tự nhiên.",
            "C. Năng lượng trong hệ kín tự động nhân đôi sau mỗi chu kỳ nhiệt động lực học.",
            "D. Mọi vật thể trong hệ kín đều giữ nguyên trạng thái chuyển động vĩnh cửu không ma sát."
        ],
        "correct_index": 0,
        "explanation": "Sự thoái hóa, bừa bộn, lười biếng và rạn nứt là mặc định tự nhiên của vũ trụ. Muốn giữ trật tự và hiệu suất cao, bạn bắt buộc phải chủ động bơm năng lượng kỷ luật mỗi ngày.",
        "trap_analysis": "Ảo tưởng ổn định vĩnh cửu: Tin rằng doanh nghiệp hay hôn nhân một khi đã tốt thì sẽ tự duy trì mà không cần bảo trì, chăm sóc."
    },
    {
        "id": "TH-MOD-03",
        "model_id": "BIOL-01",
        "model_name": "Tiến hóa & Chọn lọc Tự nhiên",
        "pillar": "Sinh học",
        "tier": 1,
        "question": "Theo thuyết tiến hóa hiện đại của Darwin, điều kiện quyết định sự sống còn của một thực thể trong môi trường biến động là gì?",
        "options": [
            "A. Khả năng thích nghi nhanh nhất với sự thay đổi của môi trường (Fitness), không phải kẻ to lớn nhất hay thông minh nhất.",
            "B. Sức mạnh cơ bắp tuyệt đối và khả năng tiêu diệt toàn bộ các cá thể xung quanh.",
            "C. Chỉ số thông minh IQ bẩm sinh cao nhất trong bầy đàn.",
            "D. Sở hữu lượng dự trữ mỡ và năng lượng nhiều nhất trong cơ thể."
        ],
        "correct_index": 0,
        "explanation": "Fitness (sự tương thích) đo lường mức độ khớp giữa thực thể và môi trường. Kẻ khổng lồ nhưng xơ cứng (như khủng long) sẽ tuyệt chủng khi môi trường biến đổi.",
        "trap_analysis": "Bẫy tối ưu hóa cục bộ quá mức: Trở nên quá hoàn hảo cho môi trường cũ đến mức mất khả năng xoay trục khi môi trường mới xuất hiện."
    },
    {
        "id": "TH-MOD-04",
        "model_id": "PSYC-01",
        "model_name": "Thiên kiến Xác nhận (Confirmation Bias)",
        "pillar": "Tâm lý học",
        "tier": 1,
        "question": "Cơ chế tâm lý sâu xa nào khiến con người mắc Thiên kiến Xác nhận (Confirmation Bias)?",
        "options": [
            "A. Bộ não muốn bảo vệ cái tôi (Ego) và tiết kiệm năng lượng nhận thức bằng cách chỉ lọc lấy thông tin củng cố niềm tin có sẵn và gạt bỏ bằng chứng phản bác.",
            "B. Do thị lực mắt người bị hạn chế không nhìn rõ toàn bộ các chữ cái trên báo chí.",
            "C. Do con người bị ảnh hưởng bởi từ trường của Trái Đất vào những ngày trăng tròn.",
            "D. Vì các công ty truyền thông cố tình không xuất bản các thông tin trái chiều."
        ],
        "correct_index": 0,
        "explanation": "Não người ghét cảm giác 'mình đã sai' (Cognitive Dissonance). Giới tinh hoa khắc phục bằng cách chủ động săn lùng các luận điểm phản bác mạnh nhất đối với niềm tin của mình.",
        "trap_analysis": "Biến niềm tin thành danh dự: Càng tranh cãi càng lún sâu vào sai lầm vì không phân biệt được bản thân mình với ý kiến của mình."
    },
    {
        "id": "TH-MOD-05",
        "model_id": "MATH-04",
        "model_name": "Giá trị Kỳ vọng & Tiêu chuẩn Kelly (Kelly Criterion)",
        "pillar": "Toán học & Xác suất",
        "tier": 1,
        "question": "Mục tiêu toán học tối thượng của Công thức Tiêu chuẩn Kelly (f* = (bp - q) / b) là gì?",
        "options": [
            "A. Tối đa hóa tốc độ tăng trưởng vốn hình học dài hạn đồng thời triệt tiêu hoàn toàn xác suất bị phá sản (Ruin Risk).",
            "B. Giúp người chơi thắng được 100% trong mọi ván cược hoặc thương vụ đầu tư.",
            "C. Tính toán chính xác thời điểm đỉnh và đáy của thị trường chứng khoán.",
            "D. Chia đều tiền cược vào tất cả các cửa có sẵn trên bàn cờ."
        ],
        "correct_index": 0,
        "explanation": "Kelly Criterion chỉ ra rằng: Có lợi thế (Edge) chưa đủ, quản trị quy mô vị thế (Position Sizing) mới là thứ quyết định bạn trở thành tỷ phú hay kẻ phá sản.",
        "trap_analysis": "Cược quá tay (Over-betting): Dù xác suất thắng là 90%, nếu bạn all-in 100% tài sản, chuỗi thua lỗ bất ngờ sẽ đưa tài sản của bạn về 0 vĩnh viễn."
    }
]

THEORY_PRINCIPLES_QUIZ = [
    {
        "id": "TH-PRIN-01",
        "principle_name": "Nguyên lý Chuyển dịch Cân bằng Le Chatelier",
        "domain": "Hóa học & Khoa học Vật liệu",
        "question": "Định nghĩa lý thuyết hình thức của Nguyên lý Le Chatelier là gì?",
        "options": [
            "A. Khi một hệ thống đang ở trạng thái cân bằng chịu một tác động bên ngoài làm thay đổi nhiệt độ, áp suất hoặc nồng độ, hệ thống sẽ tự dịch chuyển theo hướng chống lại tác động đó.",
            "B. Mọi phản ứng hóa học đều xảy ra với tốc độ không đổi bất kể nhiệt độ hay áp suất.",
            "C. Tổng khối lượng các chất tham gia phản ứng luôn lớn hơn tổng khối lượng các sản phẩm tạo thành.",
            "D. Năng lượng tỏa ra trong một phản ứng luôn bằng năng lượng hấp thụ của môi trường xung quanh."
        ],
        "correct_index": 0,
        "explanation": "Hệ thống tự nhiên luôn tìm kiếm trạng thái cân bằng nội môi. Mọi nỗ lực cưỡng bức thay đổi quá đột ngột sẽ kích hoạt phản lực đề kháng tự nhiên của hệ thống.",
        "trap_analysis": "Điều kiện biên: Hệ thống phải là hệ kín và đang ở trạng thái cân bằng động thuận nghịch."
    },
    {
        "id": "TH-PRIN-02",
        "principle_name": "Nguyên lý Chất Xúc tác (Catalysis)",
        "domain": "Hóa học & Khoa học Vật liệu",
        "question": "Cơ chế khoa học mà qua đó Chất xúc tác làm tăng tốc độ phản ứng là gì?",
        "options": [
            "A. Tạo ra một lộ trình phản ứng mới có năng lượng hoạt hóa (Activation Energy - E_a) thấp hơn mà không bị tiêu hao sau phản ứng.",
            "B. Tăng nhiệt độ của toàn bộ hệ thống lên gấp 10 lần trong tích tắc.",
            "C. Biến phản ứng thu nhiệt thành phản ứng tỏa nhiệt vĩnh cửu.",
            "D. Thay đổi vị trí cân bằng nhiệt động học cuối cùng của các chất tham gia."
        ],
        "correct_index": 0,
        "explanation": "Chất xúc tác không làm thay đổi điểm cân bằng nhiệt động học cuối cùng, nó chỉ hạ thấp bức tường cản trở ban đầu giúp phản ứng đạt đích nhanh hơn.",
        "trap_analysis": "Phép thử bác bỏ (Falsification): Nếu một chất làm thay đổi hằng số cân bằng K_eq của phản ứng thì chất đó là chất tham gia phản ứng, không phải chất xúc tác."
    },
    {
        "id": "TH-PRIN-03",
        "principle_name": "Nguyên lý Bất định Heisenberg (Uncertainty Principle)",
        "domain": "Vật lý học",
        "question": "Hệ thức Bất định Heisenberg (Δx × Δp ≥ h / 4π) khẳng định giới hạn cơ bản nào của tự nhiên?",
        "options": [
            "A. Không thể xác định đồng thời cả vị trí và động lượng của một hạt hạ nguyên tử với độ chính xác tuyệt đối; hành động đo lường làm thay đổi trạng thái của hạt.",
            "B. Vận tốc của ánh sáng trong chân không là một đại lượng hoàn toàn không thể đo đạc được.",
            "C. Thời gian trôi đi với tốc độ khác nhau tùy thuộc vào cảm xúc vui hay buồn của người quan sát.",
            "D. Mọi hạt vật chất đều có thể biến thành năng lượng nguyên tử ở nhiệt độ phòng."
        ],
        "correct_index": 0,
        "explanation": "Bất định Heisenberg là đặc tính bản chất của cơ học lượng tử, không phải do dụng cụ đo bị lỗi. Trong xã hội học, nó tương đương với Định luật Goodhart (khi một thước đo trở thành mục tiêu quản trị, nó lập tức mất giá trị đo).",
        "trap_analysis": "Hiểu sai: Nghĩ rằng đây chỉ là sự bất lực tạm thời của công nghệ đo lường hiện tại."
    }
]


def get_theory_questions_for_modes() -> List[Dict[str, Any]]:
    """Trả về bộ trắc nghiệm lý thuyết toàn diện cho 9 Chế độ Tư duy."""
    return THEORY_MODES_QUIZ


def get_theory_questions_for_models(pillar: Optional[str] = None, tier: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Sinh và tổng hợp danh sách câu hỏi trắc nghiệm lý thuyết cho 88 Mô hình Hạt nhân:
    Bao gồm các câu hỏi curated chất lượng cao + câu hỏi lý thuyết sinh tự động deterministically từ dataset.
    """
    all_models = get_all_models()
    filtered = filter_models(all_models, pillar=pillar, tier=tier)
    
    results = []
    # Add matching curated theory questions first
    for q in THEORY_MODELS_QUIZ:
        if pillar and pillar != "Tất cả" and q.get("pillar") != pillar:
            continue
        if tier is not None and q.get("tier") != tier:
            continue
        results.append(q)
        
    covered_ids = {q.get("model_id") for q in results}
    
    for m in filtered:
        if m.get("id") in covered_ids:
            continue
            
        other_models = [om for om in all_models if om.get("id") != m.get("id")]
        if len(other_models) < 3:
            continue
            
        # Deterministic shuffle using id hash seed
        seed_val = sum(ord(c) for c in m.get("id", "0"))
        rng = random.Random(seed_val)
        distractors = rng.sample(other_models, 3)
        
        raw_options = [
            (m.get("first_principle"), True),
            (distractors[0].get("first_principle"), False),
            (distractors[1].get("first_principle"), False),
            (distractors[2].get("first_principle"), False),
        ]
        rng.shuffle(raw_options)
        
        correct_idx = 0
        final_options = []
        letters = ["A", "B", "C", "D"]
        for idx, (txt, is_corr) in enumerate(raw_options):
            final_options.append(f"{letters[idx]}. {txt}")
            if is_corr:
                correct_idx = idx
                
        results.append({
            "id": f"TH-M-{m.get('id')}",
            "model_id": m.get("id"),
            "model_name": f"{m.get('name_vi')} ({m.get('name_en')})",
            "pillar": m.get("pillar"),
            "tier": m.get("tier"),
            "question": f"Về mặt lý thuyết bản chất, Chân lý gốc (First Principle) của mô hình '{m.get('name_vi')}' là gì?",
            "options": final_options,
            "correct_index": correct_idx,
            "explanation": f"Chân lý gốc của {m.get('name_vi')}: {m.get('first_principle')}. Đòn bẩy Elite: {m.get('elite_leverage')}",
            "trap_analysis": f"Bẫy đảo ngược (Inversion Trap) cần né tránh: {m.get('inversion_trap')}"
        })
        
    return results


def get_theory_questions_for_principles(domain: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Sinh và tổng hợp danh sách câu hỏi trắc nghiệm lý thuyết cho 100 Nguyên lý Khởi thủy:
    Bao gồm các câu hỏi curated chất lượng cao + câu hỏi lý thuyết sinh tự động deterministically từ dataset.
    """
    kb = load_knowledge_base()
    all_p = kb.get("principles", [])
    filtered_p = all_p
    if domain and domain != "Tất cả":
        filtered_p = [p for p in all_p if p.get("domain") == domain]
        
    results = []
    for q in THEORY_PRINCIPLES_QUIZ:
        if domain and domain != "Tất cả" and q.get("domain") != domain:
            continue
        results.append(q)
        
    covered_names = {q.get("principle_name") for q in results}
    
    for p in filtered_p:
        p_name = p.get("principle_name")
        if p_name in covered_names:
            continue
            
        other_p = [op for op in all_p if op.get("principle_name") != p_name]
        if len(other_p) < 3:
            continue
            
        seed_val = sum(ord(c) for c in p_name)
        rng = random.Random(seed_val)
        distractors = rng.sample(other_p, 3)
        
        raw_options = [
            (p.get("intuitive_summary") or p.get("description"), True),
            (distractors[0].get("intuitive_summary") or distractors[0].get("description"), False),
            (distractors[1].get("intuitive_summary") or distractors[1].get("description"), False),
            (distractors[2].get("intuitive_summary") or distractors[2].get("description"), False),
        ]
        rng.shuffle(raw_options)
        
        correct_idx = 0
        final_options = []
        letters = ["A", "B", "C", "D"]
        for idx, (txt, is_corr) in enumerate(raw_options):
            final_options.append(f"{letters[idx]}. {txt}")
            if is_corr:
                correct_idx = idx
                
        results.append({
            "id": f"TH-P-{seed_val}",
            "principle_name": p_name,
            "domain": p.get("domain", "Khoa học"),
            "question": f"Về mặt bản chất lý thuyết, nguyên lý khoa học '{p_name}' khẳng định điều gì?",
            "options": final_options,
            "correct_index": correct_idx,
            "explanation": f"Định nghĩa hình thức: {p.get('formal_definition')}. Tóm tắt trực giác: {p.get('intuitive_summary')}",
            "trap_analysis": f"Điều kiện biên: {p.get('boundary_conditions', '—')} | Khả bác: {p.get('falsification_test', '—')}"
        })
        
    return results


# =============================================================================
# 1. NGÂN HÀNG TRẮC NGHIỆM TÌNH HUỐNG 9 CHẾ ĐỘ TƯ DUY ELITE (CURATED)
# =============================================================================
MODES_QUIZ = [
    {
        "id": "MODE-01",
        "concept": "First Principles (Tư duy Nguyên bản)",
        "scenario": (
            "Khi SpaceX chế tạo tên lửa, các chuyên gia hàng không vũ trụ khẳng định: 'Chi phí mua tên lửa tối thiểu là 65 triệu USD "
            "vì lịch sử ngành hàng không chưa ai làm rẻ hơn được'. Elon Musk không chấp nhận điều này. Ông tra cứu bảng tuần hoàn hoá học, "
            "tính toán chi phí nguyên liệu thô (nhôm, titan, đồng, sợi carbon) chỉ chiếm 2% giá tên lửa, rồi tự hỏi: 'Làm thế nào để kết hợp "
            "các nguyên liệu này thành tên lửa với chi phí rẻ nhất?'"
        ),
        "question": "Elon Musk đã áp dụng phương pháp tư duy nào để đập tan niềm tin của toàn ngành hàng không?",
        "options": [
            "A. First Principles: Bóc tách về chân lý vật lý cơ bản nhất và suy luận ngược lên thay vì bắt chước (analogy)",
            "B. Tư duy Đảo ngược: Tìm cách làm cho tên lửa nổ tung để rút kinh nghiệm",
            "C. Lưỡi dao Occam: Chọn giải pháp đơn giản nhất là mua lại tên lửa cũ của Nga",
            "D. Tư duy Bậc hai: Dự đoán phản ứng của đối thủ Boeing trong 10 năm tới"
        ],
        "correct_index": 0,
        "explanation": (
            "First Principles đòi hỏi bạn không suy luận theo lối mòn bắt chước (Reasoning by Analogy). "
            "Hãy đập vụn bài toán xuống tận các định luật vật lý và nguyên liệu thô bất biến, rồi tái thiết kế từ số 0."
        ),
        "trap_analysis": (
            "Bẫy bắt chước (Analogy Trap) khiến 99% mọi người chấp nhận mức giá 65 triệu USD vì 'xưa nay người ta vẫn làm thế'. "
            "Chỉ có First Principles mới tạo ra đột phá chi phí giảm 10 lần."
        )
    },
    {
        "id": "MODE-02",
        "concept": "Tư duy Xác suất & Cập nhật Bayes (Probabilistic & Bayesian)",
        "scenario": (
            "Một nhà đầu tư theo dõi cổ phiếu công ty X. Ban đầu ông tin xác suất công ty tăng trưởng tốt là 70%. "
            "Tuy nhiên, báo cáo tài chính quý mới nhất cho thấy dòng tiền kinh doanh âm nặng dù doanh thu tăng ảo, "
            "và 2 giám đốc tài chính liên tiếp nộp đơn từ chức. Thay vì cố chấp giữ quan điểm cũ, nhà đầu tư lập tức hạ xác suất "
            "thành công của công ty xuống 25% và bán giảm tỷ trọng bảo vệ vốn."
        ),
        "question": "Hành vi của nhà đầu tư này thể hiện chế độ tư duy nào?",
        "options": [
            "A. Thiên kiến xác nhận: Cố tìm tin tốt để chứng minh mình mua đúng",
            "B. Cập nhật Bayes: Nhìn thế giới theo phổ xác suất và liên tục điều chỉnh niềm tin khi có dữ kiện thực nghiệm mới",
            "C. Chi phí cơ hội: So sánh cổ phiếu X với tiền gửi ngân hàng",
            "D. Tư duy Tùy chọn: Chấp nhận mất hết số tiền đã mua để đổi lấy cơ hội ăn 100 lần"
        ],
        "correct_index": 1,
        "explanation": (
            "Định lý Bayes dạy rằng: Niềm tin ban đầu (Prior) phải luôn được nhân với bằng chứng mới (Likelihood) "
            "để tạo ra xác suất thực tế mới (Posterior). Người tinh hoa không coi niềm tin là danh dự mà coi nó là xác suất cần cập nhật."
        ),
        "trap_analysis": (
            "Bẫy tâm lý phổ biến là Cố chấp & Nhất quán (Commitment Bias) — cố giữ niềm tin cũ dù thực tế đã đổi khác."
        )
    },
    {
        "id": "MODE-03",
        "concept": "Tư duy Đảo ngược (Inversion — Charlie Munger)",
        "scenario": (
            "Trước khi khởi động dự án phát triển phần mềm mới kéo dài 6 tháng, Giám đốc dự án tập hợp toàn bộ đội ngũ lại và nói: "
            "'Hãy tưởng tượng hôm nay là 6 tháng sau, và dự án này thất bại thảm hại, công ty bị kiện, toàn bộ dữ liệu bị mất. "
            "Bây giờ, từng người hãy viết ra chính xác những lý do gì đã dẫn tới thảm họa đó?'"
        ),
        "question": "Kỹ thuật quản trị rủi ro đỉnh cao này thuộc chế độ tư duy nào?",
        "options": [
            "A. Lạc quan tếu (Wishful Thinking)",
            "B. Tư duy Đảo ngược (Inversion / Premortem): Muốn thành công, trước hết phải tìm mọi cách thất bại chắc chắn rồi né tránh",
            "C. Đòn bẩy tài chính: Vay thêm vốn để bù lỗ nếu dự án hỏng",
            "D. Tư duy Hệ thống: Vẽ sơ đồ vòng lặp phản hồi âm"
        ],
        "correct_index": 1,
        "explanation": (
            "Charlie Munger có câu nói nổi tiếng: 'Invert, always invert' (Luôn luôn đảo ngược). "
            "Thường việc tìm cách tránh ngu ngốc dễ dàng và mang lại hiệu quả cao hơn nhiều so với việc cố gắng trở nên xuất chúng."
        ),
        "trap_analysis": (
            "Bẫy chỉ nhìn về phía trước (Forward-only Thinking) khiến người ta chỉ vẽ ra viễn cảnh màu hồng mà bỏ quên các lỗ thủng chết người."
        )
    },
    {
        "id": "MODE-04",
        "concept": "Tư duy Bậc hai (Second-Order Thinking — Howard Marks)",
        "scenario": (
            "Chính phủ áp dụng chính sách áp trần giá thuê nhà nhằm giúp người nghèo có nhà ở giá rẻ (Hệ quả bậc 1: Nhà thuê rẻ hơn). "
            "Tuy nhiên sau 2 năm, các chủ nhà ngừng xây mới và không bảo trì nhà cũ vì không có lãi. Nguồn cung nhà trọ sụt giảm nghiêm trọng, "
            "khiến hàng chục ngàn người nghèo hoàn toàn không tìm được chỗ thuê và phải ra đường (Hệ quả bậc 2)."
        ),
        "question": "Sai lầm của chính sách trên xuất phát từ việc thiếu chế độ tư duy nào?",
        "options": [
            "A. Tư duy Bậc hai (Second-Order Thinking): Không tự hỏi câu hỏi sống còn 'Và sau đó điều gì sẽ xảy ra tiếp theo?'",
            "B. Tư duy Bậc một: Chỉ nhìn vào tác động tích cực hiển hiện trước mắt",
            "C. Lưỡi dao Occam",
            "D. Quy luật Cung Cầu thuần túy"
        ],
        "correct_index": 0,
        "explanation": (
            "Tư duy bậc 1 đơn giản và thiển cận: 'Nếu làm A, B sẽ xảy ra (tốt)'. "
            "Tư duy bậc 2 sâu sắc và phức tạp hơn: 'Khi B xảy ra, các tác nhân sẽ phản ứng thế nào? Hệ quả của hệ quả đó trong 1–3 năm tới là gì?'"
        ),
        "trap_analysis": (
            "Hầu hết các thảm họa kinh tế và chính sách xã hội bắt nguồn từ tư duy bậc một: làm một điều có vẻ tốt tức thời nhưng hủy hoại hệ thống về lâu dài."
        )
    },
    {
        "id": "MODE-05",
        "concept": "Tư duy Tùy chọn & Bất đối xứng (Optionality & Barbell — Nassim Taleb)",
        "scenario": (
            "Một chuyên gia phần mềm ban ngày làm công việc lập trình hưởng lương ổn định, an toàn tuyệt đối và không có rủi ro phá sản. "
            "Buổi tối và cuối tuần, anh ta dành 2 giờ viết một thư viện mã nguồn mở và phát hành khóa học SaaS trực tuyến. "
            "Nếu khóa học thất bại, anh ta chỉ mất chút thời gian rảnh; nếu thành công lớn, phần mềm có thể phục vụ 100.000 khách hàng với chi phí cận biên bằng 0."
        ),
        "question": "Chiến lược phân bổ nguồn lực này là hiện thân hoàn hảo của chế độ tư duy nào?",
        "options": [
            "A. All-in đánh bạc toàn bộ tài sản vào một cơ hội duy nhất",
            "B. Chiến lược Barbell (Đòn tạ): Cực kỳ thận trọng ở 90% nguồn lực và cực kỳ mạo hiểm ở 10% cơ hội có lợi nhuận bất đối xứng dương",
            "C. Tư duy Đa quy mô thời gian thuần túy",
            "D. Bẫy Chi phí Chìm"
        ],
        "correct_index": 1,
        "explanation": (
            "Chiến lược Barbell của Nassim Taleb giúp bạn Chống Mong Manh (Antifragile): "
            "Giới hạn tối đa tổn thất khi rủi ro xảy ra, nhưng mở toang cánh cửa đón nhận lợi nhuận khổng lồ bất đối xứng (Asymmetric Upside)."
        ),
        "trap_analysis": (
            "Rất nhiều người rơi vào bẫy 'Rủi ro trung bình': Chọn một công việc vừa đủ bấp bênh, nhưng tiềm năng tăng trưởng lại bị chặn trần."
        )
    },
    {
        "id": "MODE-06",
        "concept": "Latticework Đa ngành (Munger Latticework)",
        "scenario": (
            "Khi xem xét nguyên nhân một sản phẩm mạng xã hội mới bùng nổ, một chuyên gia không chỉ dùng kinh tế học (tiếp thị, giá cả), "
            "mà kết hợp: Vật lý (Khối lượng tới hạn để tạo phản ứng dây chuyền), Sinh học (Tiến hóa thích nghi với thị hiếu người dùng), "
            "và Tâm lý học (Bằng chứng xã hội & Thiên kiến FOMO)."
        ),
        "question": "Chuyên gia này đang vận dụng phương pháp gì?",
        "options": [
            "A. Hội chứng người cầm búa (Man with a Hammer)",
            "B. Mạng lưới mô hình đa ngành (Latticework): Kết hợp lăng kính của nhiều môn khoa học cơ bản để tạo hiệu ứng cộng hưởng Lollapalooza",
            "C. Chuyên môn hóa hẹp (Silo Thinking)",
            "D. Lưỡi dao Occam"
        ],
        "correct_index": 1,
        "explanation": (
            "Thế giới thực không phân chia theo khoa học tự nhiên hay khoa học xã hội. Mọi vấn đề lớn đều là hệ thống phức hợp. "
            "Latticework giúp bạn treo mọi kinh nghiệm lên các mô hình cốt lõi liên ngành."
        ),
        "trap_analysis": (
            "Người cầm búa chỉ nhìn thấy đinh; chuyên gia một ngành duy nhất luôn bóp méo thực tế để vừa vặn với chuyên môn hạn hẹp của mình."
        )
    },
    {
        "id": "MODE-07",
        "concept": "Vòng lặp Thực nghiệm Nhanh (Iterative Loops & Lean)",
        "scenario": (
            "Thay vì bỏ 1 tỷ đồng và 1 năm để xây dựng một ứng dụng giao đồ ăn hoàn chỉnh rồi mới ra mắt thị trường, "
            "nhóm sáng lập tạo một nhóm Zalo đơn giản trong khu chung cư 500 hộ để nhận đặt món thủ công, đo lường tỷ lệ đặt lại hàng tuần, "
            "và liên tục tinh chỉnh dịch vụ sau mỗi 3 ngày."
        ),
        "question": "Phương pháp tiếp cận này thể hiện bản chất của chế độ tư duy nào?",
        "options": [
            "A. Vòng lặp Thực nghiệm Nhanh (Build - Measure - Learn): Thay giả định trừu tượng bằng thử nghiệm vi mô chi phí thấp để tiếp xúc sự thật sớm nhất",
            "B. Tư duy Bậc hai",
            "C. Đòn bẩy tài chính lớn",
            "D. Vòng tròn Năng lực cố định"
        ],
        "correct_index": 0,
        "explanation": (
            "Trong môi trường bất định, không kế hoạch trên giấy nào sống sót sau lần tiếp xúc đầu tiên với khách hàng. "
            "Tốc độ học hỏi qua các vòng lặp thực nghiệm vi mô quyết định sự sống còn."
        ),
        "trap_analysis": (
            "Bẫy Phân tích tê liệt (Analysis Paralysis): Ngồi trong phòng lạnh lập kế hoạch 5 năm mà không chịu đưa sản phẩm ra va đập thực tế."
        )
    },
    {
        "id": "MODE-08",
        "concept": "Lý thuyết Trò chơi & Động lực (Game Theory & Incentives)",
        "scenario": (
            "Một công ty muốn giảm tỷ lệ tài xế giao hàng trễ giờ. Nếu chỉ tuyên truyền đạo đức và kêu gọi trách nhiệm, kết quả không thay đổi. "
            "Nhưng khi công ty đổi cơ chế thưởng: Tài xế giao đúng giờ được cộng 15% tiền thưởng chuyến, nhưng nếu vi phạm quá 3 lần/tháng "
            "sẽ bị tạm ngưng nhận cuốc vào giờ cao điểm, tỷ lệ đúng giờ lập tức tăng lên 98%."
        ),
        "question": "Nguyên lý cốt lõi nào đã thay đổi cục diện?",
        "options": [
            "A. Quyền lực cưỡng chế",
            "B. Thiết kế động lực (Incentive Design): 'Hãy cho tôi thấy cơ chế đãi ngộ, tôi sẽ chỉ cho bạn thấy hành vi của con người' (Charlie Munger)",
            "C. Lưỡi dao Occam",
            "D. Thiên kiến sống sót"
        ],
        "correct_index": 1,
        "explanation": (
            "Con người phản ứng với các động lực (Incentives), không phải khẩu hiệu. "
            "Khi động lực được thiết kế căn chỉnh chuẩn xác (Aligned Incentives), hành vi tự giác xuất hiện mà không cần giám sát nặng nề."
        ),
        "trap_analysis": (
            "Ngây thơ tin rằng mọi người sẽ hành động vì lợi ích chung khi mà cơ chế tài chính ngầm đang khuyến khích họ làm điều ngược lại."
        )
    },
    {
        "id": "MODE-09",
        "concept": "Đa quy mô Thời gian (Multi-Scale Time Horizons — Jeff Bezos)",
        "scenario": (
            "Jeff Bezos nói với cổ đông Amazon: 'Nếu mọi việc bạn làm đòi hỏi phải có kết quả trong 3 năm, bạn sẽ phải cạnh tranh với hàng ngàn người. "
            "Nhưng nếu bạn sẵn sàng đầu tư vào một tầm nhìn 7–10 năm, bạn chỉ phải cạnh tranh với một số rất ít người, vì hầu như không ai kiên nhẫn đến thế'."
        ),
        "question": "Chế độ tư duy nào là bí quyết giúp xây dựng các tổ chức và con người vĩ đại trường tồn?",
        "options": [
            "A. Tối ưu hóa lợi nhuận quý này bằng mọi giá",
            "B. Tư duy Đa quy mô Thời gian: Hành động quyết liệt hôm nay nhưng neo giữ tầm nhìn vào những nguyên lý không thay đổi trong 10 năm tới",
            "C. Bắt chước đối thủ nhanh nhất có thể",
            "D. Thiên kiến sẵn có"
        ],
        "correct_index": 1,
        "explanation": (
            "Đa quy mô thời gian giúp giải quyết mâu thuẫn giữa hành động vi mô hàng ngày và chiến lược vĩ mô dài hạn. "
            "Lãi kép và moat lớn nhất của con người luôn nằm ở quy mô thời gian 10 năm."
        ),
        "trap_analysis": (
            "Bẫy thiển cận (Hyperbolic Discounting): Não bộ con người có xu hướng định giá quá cao phần thưởng tức thì và đánh giá quá thấp giá trị khổng lồ của tương lai xa."
        )
    }
]

# =============================================================================
# 2. NGÂN HÀNG TRẮC NGHIỆM TÌNH HUỐNG 88 MÔ HÌNH HẠT NHÂN (CURATED)
# =============================================================================
MODELS_QUIZ = [
    {
        "id": "Q-PHYS-01",
        "model_id": "PHYS-01",
        "pillar": "Vật lý học",
        "tier": 1,
        "model_name": "Đòn bẩy (Leverage)",
        "scenario": (
            "Một nhà sáng tạo nội dung tạo ra một cuốn Ebook và một chuỗi video bài giảng. Sau khi hoàn thành sản phẩm, "
            "dù có 10 người mua hay 100.000 người mua, anh ta hầu như không tốn thêm bất kỳ giờ lao động nào để phục vụ. "
            "Doanh thu tăng gấp vạn lần trong khi chi phí biên gần bằng 0."
        ),
        "question": "Mô hình hạt nhân nào từ Vật lý học được áp dụng ở đây?",
        "options": [
            "A. Quán tính",
            "B. Đòn bẩy không cần sự cho phép (Code & Media Leverage)",
            "C. Khối lượng tới hạn",
            "D. Entropy"
        ],
        "correct_index": 1,
        "explanation": "Đòn bẩy là khả năng khuếch đại nỗ lực nhỏ thành kết quả khổng lồ. Code và Media là hai loại đòn bẩy tối thượng của thế kỷ 21.",
        "trap_analysis": "Đòn bẩy hai chiều: Nếu áp dụng đòn bẩy tài chính (Margin) mà không có biên độ an toàn, bạn sẽ bị khuếch đại sự phá sản."
    },
    {
        "id": "Q-PHYS-03",
        "model_id": "PHYS-03",
        "pillar": "Vật lý học",
        "tier": 1,
        "model_name": "Entropy & Định luật 2 Nhiệt động học",
        "scenario": (
            "Một công ty khởi nghiệp sau 3 năm phát triển rất thành công bắt đầu xuất hiện tình trạng: quy trình giấy tờ rườm rà, "
            "nhân sự tị nạnh công việc, giao tiếp giữa các phòng ban bị tắc nghẽn, dù ban giám đốc không hề cố ý tạo ra những điều đó."
        ),
        "question": "Quy luật vật lý vũ trụ nào chi phối sự suy thoái tự nhiên này?",
        "options": [
            "A. Entropy: Trong một hệ kín, sự hỗn loạn và thoái hóa luôn tự động tăng dần nếu không được nạp thêm năng lượng bảo trì",
            "B. Bảo toàn động lượng",
            "C. Thuyết tương đối",
            "D. Hiện tượng chuyển pha"
        ],
        "correct_index": 0,
        "explanation": "Entropy là mặc định của vũ trụ. Không làm gì cả không có nghĩa là giữ nguyên, mà là tự suy thoái. Tổ chức muốn trật tự phải liên tục bơm năng lượng kiểm tra và tối ưu.",
        "trap_analysis": "Bẫy ảo tưởng tự ổn định: Tin rằng một cỗ máy hay một mối quan hệ một khi đã tốt đẹp thì sẽ tự vận hành hoàn hảo mãi mãi."
    },
    {
        "id": "Q-BIOL-01",
        "model_id": "BIOL-01",
        "pillar": "Sinh học",
        "tier": 1,
        "model_name": "Tiến hóa & Chọn lọc Tự nhiên",
        "scenario": (
            "Trong cuộc khủng hoảng thị trường năm 2008 và đại dịch 2020, hàng ngàn doanh nghiệp khổng lồ, hùng mạnh nhưng xơ cứng bị phá sản. "
            "Ngược lại, các doanh nghiệp vừa và nhỏ có khả năng xoay trục linh hoạt sang kinh doanh online lại tồn tại và phát triển rực rỡ."
        ),
        "question": "Chân lý sinh học nào của Charles Darwin được chứng thực ở đây?",
        "options": [
            "A. Kẻ mạnh nhất hoặc thông minh nhất sẽ sống sót",
            "B. Không phải kẻ mạnh nhất, mà chính kẻ thích nghi nhanh nhất với sự thay đổi của môi trường mới là kẻ sống sót",
            "C. Cạnh tranh cùng loài luôn tiêu diệt hết mọi giống loài",
            "D. Đồng sinh tuyệt đối"
        ],
        "correct_index": 1,
        "explanation": "Chọn lọc tự nhiên đào thải những thực thể không khớp với môi trường mới. Sự linh hoạt và khả năng biến dị có kiểm soát là chìa khóa sinh tồn.",
        "trap_analysis": "Bẫy tối ưu hóa quá mức cho hiện tại: Một loài quá chuyên biệt cho một môi trường duy nhất sẽ tuyệt chủng ngay khi môi trường đó đổi thay."
    },
    {
        "id": "Q-BIOL-04",
        "model_id": "BIOL-04",
        "pillar": "Sinh học",
        "tier": 1,
        "model_name": "Hiệu ứng Nữ hoàng Đỏ (Red Queen Effect)",
        "scenario": (
            "Trong ngành bán lẻ điện máy, hai chuỗi cửa hàng lớn liên tục đầu tư hàng triệu USD nâng cấp app, rút ngắn thời gian giao hàng "
            "từ 2 giờ xuống 1 giờ, tăng khuyến mãi. Nhưng sau 3 năm, thị phần của cả hai bên vẫn giữ nguyên 40% - 40% và biên lợi nhuận bị bào mòn."
        ),
        "question": "Mô hình sinh học nào mô tả trạng thái 'phải chạy hết sức chỉ để đứng yên một chỗ' này?",
        "options": [
            "A. Hốc sinh thái",
            "B. Hiệu ứng Nữ hoàng Đỏ (Red Queen Effect trong thuyết đồng tiến hóa săn mồi - con mồi)",
            "C. Gen vị kỷ",
            "D. Thắt cổ chai di truyền"
        ],
        "correct_index": 1,
        "explanation": "Trong môi trường có đối thủ cạnh tranh cùng tiến hóa, việc bạn nỗ lực không giúp bạn vượt lên mà chỉ giúp bạn không bị đào thải. Muốn bứt phá phải đổi hốc sinh thái.",
        "trap_analysis": "Chạy đua vũ trang không lối thoát: Tiêu tốn toàn bộ tài nguyên chỉ để duy trì vị thế hiện tại thay vì tìm một con đường hoàn toàn mới."
    },
    {
        "id": "Q-PSYC-01",
        "model_id": "PSYC-01",
        "pillar": "Tâm lý học",
        "tier": 1,
        "model_name": "Thiên kiến Xác nhận (Confirmation Bias)",
        "scenario": (
            "Sau khi mua một mã cổ phiếu bất động sản, nhà đầu tư chỉ tìm đọc các bài phân tích khen ngợi tiềm năng của công ty, "
            "tham gia các diễn đàn của những người cùng mua cổ phiếu đó để tán dương lẫn nhau, và lập tức chê bai hoặc bỏ qua "
            "mọi bài báo cảnh báo về rủi ro pháp lý và nợ trái phiếu của doanh nghiệp."
        ),
        "question": "Thiên kiến tâm lý nguy hiểm nào đang che mờ mắt nhà đầu tư này?",
        "options": [
            "A. Thiên kiến Xác nhận (Confirmation Bias): Chỉ thu nạp thông tin củng cố niềm tin có sẵn và gạt bỏ bằng chứng phản bác",
            "B. Hiệu ứng Mỏ neo",
            "C. Hiệu ứng Tương phản",
            "D. Hiệu ứng Hào quang"
        ],
        "correct_index": 0,
        "explanation": "Bộ não người muốn bảo vệ cái tôi bằng cách chỉ tìm kiếm bằng chứng ủng hộ kết luận đã chọn. Khắc phục bằng cách chủ động tìm kiếm lý do tại sao mình sai.",
        "trap_analysis": "Confirmation bias là nguyên nhân số một dẫn tới việc gồng lỗ và phá sản trong đầu tư tài chính."
    },
    {
        "id": "Q-PSYC-05",
        "model_id": "PSYC-05",
        "pillar": "Tâm lý học",
        "tier": 1,
        "model_name": "Hiệu ứng Lollapalooza (Charlie Munger)",
        "scenario": (
            "Trong một buổi đấu giá từ thiện sôi động, một người bình thường vốn rất tiết kiệm đã bỏ ra số tiền gấp 10 lần giá trị thật "
            "để mua một bức tranh. Phân tích cho thấy sự cộng hưởng đồng thời của: Bằng chứng xã hội (đám đông hò reo), "
            "Ác cảm mất mát (sợ người khác cướp mất), Thiên kiến nhất quán (đã lỡ giơ biển trả giá 3 lần), và Hiệu ứng tương phản."
        ),
        "question": "Charlie Munger gọi hiện tượng nhiều xu hướng tâm lý cùng đẩy về một hướng tạo ra sức mạnh hủy diệt này là gì?",
        "options": [
            "A. Hiệu ứng Mỏ neo đơn lẻ",
            "B. Hiệu ứng Lollapalooza: Sự hội tụ cộng hưởng đa chiều dẫn tới hành vi bùng nổ phi lý trí cực độ",
            "C. Thuyết tương đối xã hội",
            "D. Định luật Gresham"
        ],
        "correct_index": 1,
        "explanation": "1 + 1 không bằng 2 mà bằng 10 khi 3-4 thiên kiến tâm lý tác động cùng một lúc. Nhận diện Lollapalooza giúp bạn né tránh bong bóng tài chính và các thảm họa cuộc đời.",
        "trap_analysis": "Coi thường sức mạnh cộng hưởng: Nghĩ rằng từng yếu tố nhỏ không đáng lo ngại mà quên mất sự kết hợp của chúng có thể làm sập cả một đế chế."
    },
    {
        "id": "Q-ECON-02",
        "model_id": "ECON-02",
        "pillar": "Kinh tế học",
        "tier": 1,
        "model_name": "Chi phí Cơ hội (Opportunity Cost)",
        "scenario": (
            "Một bạn trẻ dành 4 giờ mỗi tối để cày phim giải trí miễn phí trên mạng và nghĩ rằng: 'Mình xem phim miễn phí nên chẳng mất đồng nào'. "
            "Một cố vấn tư duy chỉ ra: 'Bạn đang trả giá bằng 4 giờ có thể dùng để học lập trình, tập thể dục, hoặc xây dựng mối quan hệ giá trị'."
        ),
        "question": "Cố vấn tư duy đang áp dụng khái niệm kinh tế học cơ bản nào?",
        "options": [
            "A. Chi phí cơ hội: Giá trị của phương án tốt nhất bị bỏ qua khi bạn đưa ra một lựa chọn",
            "B. Chi phí cận biên",
            "C. Quy luật Cung Cầu",
            "D. Hiệu ứng Mạng lưới"
        ],
        "correct_index": 0,
        "explanation": "Không có gì là miễn phí. Chi phí thực sự của bất kỳ hành động nào chính là điều giá trị nhất mà bạn ĐÃ KHÔNG THỂ LÀM trong khoảng thời gian đó.",
        "trap_analysis": "Chỉ nhìn thấy chi phí bằng tiền mặt (Explicit cost) mà hoàn toàn mù tịt trước chi phí thời gian và tiềm năng bị mất (Implicit cost)."
    },
    {
        "id": "Q-ECON-04",
        "model_id": "ECON-04",
        "pillar": "Kinh tế học",
        "tier": 1,
        "model_name": "Hiệu ứng Mạng lưới (Network Effects)",
        "scenario": (
            "Một ứng dụng nhắn tin mới ra mắt có giao diện đẹp hơn Zalo và nhiều tính năng vượt trội hơn, nhưng người dùng cài thử rồi lại xoá "
            "vì bạn bè, gia đình và đồng nghiệp của họ đều đang ở trên Zalo. Ứng dụng mới không thể lôi kéo được người dùng."
        ),
        "question": "Con hào kinh tế bất khả xâm phạm nào đang bảo vệ Zalo?",
        "options": [
            "A. Chi phí sản xuất thấp",
            "B. Hiệu ứng Mạng lưới (Network Effects): Giá trị của hệ thống tăng theo cấp số nhân với mỗi người dùng mới tham gia (Định luật Metcalfe)",
            "C. Đòn bẩy tài chính",
            "D. Phá hủy sáng tạo"
        ],
        "correct_index": 1,
        "explanation": "Sản phẩm tốt hơn chưa chắc thắng sản phẩm có mạng lưới lớn hơn. Mỗi nút mạng gia nhập làm tăng giá trị cho tất cả các nút mạng còn lại.",
        "trap_analysis": "Đầu tư vào sản phẩm chỉ chăm chăm làm tính năng tốt hơn mà không có cơ chế tích lũy hiệu ứng mạng lưới."
    },
    {
        "id": "Q-MATH-02",
        "model_id": "MATH-02",
        "pillar": "Toán học & Xác suất",
        "tier": 1,
        "model_name": "Định luật Lũy thừa & Pareto 80/20",
        "scenario": (
            "Phân tích doanh thu của một công ty cho thấy: trong số 100 sản phẩm đang bán, chỉ có 20 sản phẩm mang lại 80% tổng lợi nhuận ròng. "
            "80 sản phẩm còn lại làm tiêu tốn 80% thời gian hỗ trợ khách hàng, kho bãi và vận hành nhưng chỉ đem về 20% lợi nhuận."
        ),
        "question": "Mô hình phân phối toán học nào giải thích hiện tượng phân bổ bất đối xứng này?",
        "options": [
            "A. Phân phối Chuẩn hình chuông Gauss",
            "B. Định luật Lũy thừa & Nguyên lý Pareto 80/20: Mối quan hệ bất đối xứng giữa đầu vào và đầu ra",
            "C. Hồi quy về trung bình",
            "D. Nghịch lý Simpson"
        ],
        "correct_index": 1,
        "explanation": "Thế giới không phân phối đồng đều. 20% nguyên nhân tạo ra 80% kết quả. Giới tinh hoa tập trung tối đa nguồn lực vào 20% nòng cốt này.",
        "trap_analysis": "Dàn trải nguồn lực cào bằng: Đối xử bình đẳng với mọi công việc, dẫn đến cạn kiệt năng lượng mà không tạo ra đột phá."
    },
    {
        "id": "Q-SYST-02",
        "model_id": "SYST-02",
        "pillar": "Kỹ thuật & Hệ thống",
        "tier": 1,
        "model_name": "Biên độ An toàn (Margin of Safety)",
        "scenario": (
            "Khi các kỹ sư xây một cây cầu dự kiến chỉ chở tối đa xe tải nặng 10 tấn, họ thiết kế cây cầu có sức chịu tải thực tế lên tới 30 tấn. "
            "Tương tự, khi Warren Buffett định giá một công ty có giá trị thực 100.000 đồng/cổ phiếu, ông chỉ mua khi giá thị trường rớt xuống dưới 65.000 đồng."
        ),
        "question": "Nguyên lý kỹ thuật và đầu tư cốt lõi này có tên là gì?",
        "options": [
            "A. Tối ưu hóa hiệu suất tối đa",
            "B. Biên độ An toàn (Margin of Safety): Tạo lớp đệm dự phòng chống lại sai số trong tính toán và những cú sốc bất ngờ",
            "C. Vòng phản hồi dương",
            "D. Nút cổ chai"
        ],
        "correct_index": 1,
        "explanation": "Tương lai vốn bất định và không thể dự báo chính xác. Biên độ an toàn giúp bạn sống sót ngay cả khi bạn tính toán sai hoặc gặp thiên nga đen.",
        "trap_analysis": "Vận hành hệ thống ở mức công suất 100% không có dự phòng; chỉ cần một cú xóc nhỏ là toàn bộ hệ thống sụp đổ."
    }
]

# =============================================================================
# 3. NGÂN HÀNG TRẮC NGHIỆM TÌNH HUỐNG 100 NGUYÊN LÝ KHỞI THỦY (CURATED)
# =============================================================================
PRINCIPLES_QUIZ = [
    {
        "id": "Q-PRIN-01",
        "principle_name": "Nguyên lý Chuyển dịch Cân bằng Le Chatelier",
        "domain": "Hóa học & Khoa học Vật liệu",
        "scenario": (
            "Khi một người lãnh đạo mới về một phòng ban đang vận hành ổn định và ngay lập tức ban hành hàng loạt nội quy thắt chặt đột ngột, "
            "nhân viên không công khai phản đối nhưng ngầm làm việc chậm lại, xin nghỉ ốm nhiều hơn, khiến năng suất tụt giảm trầm trọng."
        ),
        "question": "Nguyên lý tự nhiên nào giải thích phản ứng kháng cự tự động này của hệ thống?",
        "options": [
            "A. Định luật Bảo toàn Khối lượng",
            "B. Nguyên lý Le Chatelier: Khi một hệ thống cân bằng bị cưỡng bức thay đổi, nó sẽ tự động sinh phản lực chống lại sự thay đổi đó",
            "C. Định luật Vạn vật hấp dẫn",
            "D. Nguyên lý Bất định Heisenberg"
        ],
        "correct_index": 1,
        "explanation": "Muốn thay đổi một hệ thống đang cân bằng bền, không thể dùng bạo lực áp đặt tức thời mà phải tăng nhiệt độ từ từ hoặc dịch chuyển điều kiện biên khéo léo.",
        "trap_analysis": "Ảo tưởng có thể ép buộc con người hoặc tổ chức thay đổi mà không phải trả giá bằng phản lực nội tại."
    },
    {
        "id": "Q-PRIN-02",
        "principle_name": "Nguyên lý Chất Xúc tác (Catalysis)",
        "domain": "Hóa học & Khoa học Vật liệu",
        "scenario": (
            "Hai nhóm sinh viên cùng tham gia nghiên cứu khoa học. Nhóm A cặm cụi đọc tài liệu giấy và dịch thủ công từng trang, mất 3 tháng. "
            "Nhóm B dùng công cụ AI tổng hợp tài liệu và lập trình mã nguồn, hoàn thành nghiên cứu chỉ sau 1 tuần với chất lượng tương đương."
        ),
        "question": "Công cụ AI đóng vai trò gì trong phản ứng nghiên cứu khoa học theo nguyên lý hóa học?",
        "options": [
            "A. Chất phản ứng bị tiêu hao",
            "B. Chất Xúc tác (Catalyst): Làm hạ thấp năng lượng hoạt hóa (rào cản độ khó) giúp phản ứng xảy ra nhanh gấp bội mà không bị hao mòn",
            "C. Chất ức chế",
            "D. Sản phẩm phụ"
        ],
        "correct_index": 1,
        "explanation": "Người thông minh không dùng bạo lực vượt qua rào cản năng lượng; họ tìm kiếm chất xúc tác (công nghệ, quy trình, mạng lưới) để hạ độ khó xuống.",
        "trap_analysis": "Cố chấp làm việc theo lối khổ hạnh, xem thường các đòn bẩy xúc tác hiện đại."
    },
    {
        "id": "Q-PRIN-03",
        "principle_name": "Nguyên lý Bất định Heisenberg (Uncertainty Principle)",
        "domain": "Vật lý học",
        "scenario": (
            "Khi ban giám đốc lắp đặt camera giám sát chi tiết từng bàn làm việc và đo số lần gõ phím của lập trình viên, "
            "họ nhận thấy các lập trình viên bắt đầu gõ phím liên tục các dòng code rác vô nghĩa để đối phó, trong khi chất lượng phần mềm thực sự đi xuống."
        ),
        "question": "Hiện tượng 'hành động quan sát làm biến dạng chính đối tượng bị quan sát' phản ánh nguyên lý nào?",
        "options": [
            "A. Định luật 1 Newton",
            "B. Nguyên lý Bất định Heisenberg & Hiệu ứng Người quan sát (Observer Effect / Định luật Goodhart)",
            "C. Định luật Ohm",
            "D. Định luật Coulomb"
        ],
        "correct_index": 1,
        "explanation": "Trong vật lý lượng tử cũng như trong khoa học xã hội: khi một thước đo trở thành mục tiêu quản lý, nó lập tức không còn là một thước đo tốt nữa.",
        "trap_analysis": "Tin rằng có thể đo lường và giám sát con người một cách hoàn toàn khách quan mà không làm thay đổi tâm lý và hành vi của họ."
    },
    {
        "id": "Q-PRIN-04",
        "principle_name": "Định luật Gresham (Gresham's Law)",
        "domain": "Kinh tế học & Tiền tệ",
        "scenario": (
            "Trong một môi trường làm việc mà những người giỏi, trung thực, cống hiến thật sự không được công nhận, "
            "trong khi những kẻ nịnh bợ, làm màu lại được thăng tiến, dần dần những người tài năng nộp đơn nghỉ việc hết, chỉ còn lại những kẻ nịnh bợ."
        ),
        "question": "Định luật kinh tế học kinh điển nào được diễn đạt qua câu 'Tiền xấu đuổi tiền tốt'?",
        "options": [
            "A. Định luật Cung Cầu",
            "B. Định luật Gresham: Khi tiền xấu và tiền tốt cùng lưu hành theo mệnh giá pháp định, tiền xấu sẽ đánh bật tiền tốt ra khỏi lưu thông",
            "C. Hiệu ứng Mạng lưới",
            "D. Nghịch lý Giá trị của Kim cương và Nước"
        ],
        "correct_index": 1,
        "explanation": "Nếu tổ chức không có cơ chế thanh lọc nghiêm ngặt, cái xấu/chất lượng kém sẽ tích tụ và đuổi sạch các giá trị tinh hoa ra ngoài.",
        "trap_analysis": "Bẫy thờ ơ với tiêu chuẩn: Nghĩ rằng dung túng một vài nhân sự yếu kém sẽ không ảnh hưởng tới nhân sự xuất sắc."
    }
]


# =============================================================================
# 4. ACTIVE RECALL FLASHCARDS GENERATOR
# =============================================================================
def get_all_flashcards(filter_type: str = "models", pillar: Optional[str] = None, tier: Optional[int] = None) -> List[Dict[str, Any]]:
    """Tạo danh sách thẻ Flashcard chuẩn hóa từ cơ sở dữ liệu để phục vụ Active Recall."""
    cards = []

    if filter_type in ("models", "all"):
        all_models = get_all_models()
        models = filter_models(all_models, pillar=pillar, tier=tier)
        for m in models:
            cards.append({
                "id": m.get("id"),
                "type": "model",
                "category": "88 Mô hình Hạt nhân",
                "pillar": m.get("pillar"),
                "tier": m.get("tier"),
                "name_vi": m.get("name_vi"),
                "name_en": m.get("name_en"),
                # Mặt trước: Câu hỏi kích hoạt 5 giây
                "front_trigger": m.get("trigger_question") or f"Làm thế nào để nhận diện và vận dụng mô hình {m.get('name_vi')}?",
                "front_badge": f"🏛️ {m.get('pillar')} · Tier {m.get('tier')}",
                # Mặt sau: Bản chất gốc rễ & đòn bẩy
                "back_principle": m.get("first_principle"),
                "back_leverage": m.get("elite_leverage"),
                "back_trap": m.get("inversion_trap"),
                "back_lollapalooza": ", ".join(m.get("lollapalooza_pairs", [])),
            })

    if filter_type in ("modes", "all") and not pillar and not tier:
        for q in MODES_QUIZ:
            cards.append({
                "id": q.get("id"),
                "type": "mode",
                "category": "9 Chế độ Tư duy",
                "pillar": "Chế độ Tư duy Elite",
                "tier": 1,
                "name_vi": q.get("concept"),
                "name_en": "Elite Mode",
                "front_trigger": f"Khi nào nên kích hoạt chế độ: {q.get('concept')}?",
                "front_badge": "🧠 9 Chế độ Tư duy Tinh hoa",
                "back_principle": q.get("explanation"),
                "back_leverage": q.get("scenario"),
                "back_trap": q.get("trap_analysis"),
                "back_lollapalooza": "First Principles, Inversion, Bayesian",
            })

    if filter_type in ("principles", "all") and not tier:
        kb = load_knowledge_base()
        for p in kb.get("principles", []):
            if pillar and pillar != "Tất cả" and p.get("domain") != pillar:
                continue
            cards.append({
                "id": p.get("principle_name"),
                "type": "principle",
                "category": "100 Nguyên lý Khởi thủy",
                "pillar": p.get("domain", "Nguyên lý Khoa học"),
                "tier": p.get("tier", 1),
                "name_vi": p.get("principle_name"),
                "name_en": p.get("principle_name"),
                "front_trigger": f"💡 Chân lý bất biến của '{p.get('principle_name')}' là gì và khi nào nó bị phá vỡ?",
                "front_badge": f"🔬 {p.get('domain', 'Khoa học')}",
                "back_principle": p.get("intuitive_summary") or p.get("description"),
                "back_leverage": p.get("formal_definition"),
                "back_trap": f"Điều kiện biên: {p.get('boundary_conditions', '—')} | Khả bác: {p.get('falsification_test', '—')}",
                "back_lollapalooza": p.get("domain", ""),
            })

    return cards


# =============================================================================
# 5. USER PROGRESS & MASTERY TRACKING
# =============================================================================
def record_quiz_completion(username: str, quiz_category: str, score: int, total: int) -> Dict[str, Any]:
    """Lưu kết quả trắc nghiệm vào lịch sử người dùng."""
    hist = load_user_history(username)
    quiz_stats = hist.setdefault("quiz_stats", {
        "total_quizzes_taken": 0,
        "total_questions_answered": 0,
        "total_correct_answers": 0,
        "recent_tests": []
    })

    quiz_stats["total_quizzes_taken"] += 1
    quiz_stats["total_questions_answered"] += total
    quiz_stats["total_correct_answers"] += score

    entry = {
        "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "category": quiz_category,
        "score": score,
        "total": total,
        "percentage": round((score / total * 100), 1) if total > 0 else 0
    }
    quiz_stats["recent_tests"].insert(0, entry)
    quiz_stats["recent_tests"] = quiz_stats["recent_tests"][:30]

    save_user_history(username, hist)
    return quiz_stats


def update_flashcard_mastery(username: str, item_id: str, status: str) -> Dict[str, Any]:
    """
    Cập nhật trạng thái nhớ thẻ Flashcard:
    status in ['mastered' (Đã thuộc), 'learning' (Nhớ mang máng), 'review_needed' (Chưa nhớ)]
    """
    hist = load_user_history(username)
    flashcards = hist.setdefault("flashcards_mastery", {
        "mastered": [],
        "learning": [],
        "review_needed": []
    })

    for s in ["mastered", "learning", "review_needed"]:
        if item_id in flashcards.get(s, []):
            flashcards[s].remove(item_id)

    if status in flashcards:
        flashcards[status].append(item_id)

    save_user_history(username, hist)
    return flashcards


def get_user_mastery_summary(username: str) -> Dict[str, Any]:
    """Tính toán thống kê tỷ lệ làm chủ kiến thức."""
    hist = load_user_history(username)
    quiz_stats = hist.get("quiz_stats", {
        "total_quizzes_taken": 0,
        "total_questions_answered": 0,
        "total_correct_answers": 0,
        "recent_tests": []
    })
    flashcards = hist.get("flashcards_mastery", {
        "mastered": [],
        "learning": [],
        "review_needed": []
    })

    total_ans = quiz_stats.get("total_questions_answered", 0)
    total_corr = quiz_stats.get("total_correct_answers", 0)
    accuracy = round(total_corr / total_ans * 100, 1) if total_ans > 0 else 0.0

    mastered_count = len(flashcards.get("mastered", []))
    learning_count = len(flashcards.get("learning", []))
    review_count = len(flashcards.get("review_needed", []))

    # Tỷ lệ làm chủ trên tổng số 88 mô hình hạt nhân cốt lõi
    mastery_pct = round(mastered_count / 88 * 100, 1)

    return {
        "accuracy": accuracy,
        "total_quizzes": quiz_stats.get("total_quizzes_taken", 0),
        "mastered_count": mastered_count,
        "learning_count": learning_count,
        "review_count": review_count,
        "mastery_pct": min(100.0, mastery_pct),
        "recent_tests": quiz_stats.get("recent_tests", [])
    }


# =============================================================================
# 6. AI DYNAMIC QUIZ GENERATOR & FEYNMAN EVALUATION (GEMINI MULTI-KEY)
# =============================================================================
def _normalize_keys(api_keys: Union[str, List[str], tuple]) -> List[str]:
    if isinstance(api_keys, str):
        raw = [k.strip() for k in api_keys.split(",") if k.strip()]
    elif isinstance(api_keys, (list, tuple)):
        raw = [str(k).strip() for k in api_keys if str(k).strip()]
    else:
        raw = []
    seen = set()
    res = []
    for k in raw:
        if k and k not in seen:
            seen.add(k)
            res.append(k)
    return res


def generate_ai_quiz(
    api_keys: Union[str, List[str], tuple],
    model_name: str,
    category: str,
    topic: str = "Đầu tư CKVN, Khởi nghiệp & Đời sống",
    num_questions: int = 3
) -> Optional[List[Dict[str, Any]]]:
    """Sinh bộ câu hỏi trắc nghiệm tình huống mới toanh bằng AI qua Gemini đa khóa."""
    keys = _normalize_keys(api_keys)
    if not keys:
        return None

    prompt = f"""Bạn là Huấn luyện viên Tư duy Tinh hoa (Elite Mental Models Coach).
Hãy tạo {num_questions} câu hỏi trắc nghiệm tình huống thực tế hóc búa để kiểm tra phản xạ nhận diện mô hình/nguyên lý.

Danh mục yêu cầu: {category}
Chủ đề / Bối cảnh: {topic}

Yêu cầu BẮT BUỘC:
1. KHÔNG hỏi lý thuyết suông kiểu "Mô hình X là gì?". Mỗi câu PHẢI là một tình huống đời thực sinh động (Case Study) trong đầu tư, kinh doanh, hoặc học đường.
2. 4 phương án lựa chọn (A, B, C, D). Các phương án sai phải là các bẫy ngụy biện tâm lý hoặc hiểu lầm phổ biến.
3. Giải thích sâu sắc từ Chân lý gốc (First Principles) và chỉ rõ Bẫy ngụy biện của các đáp án sai.
4. Trả về DUY NHẤT một chuỗi JSON hợp lệ (không markdown block, không giải thích ngoài JSON).

Cấu trúc JSON:
[
  {{
    "id": "AI-Q-01",
    "concept": "Tên mô hình hoặc chế độ",
    "scenario": "Tình huống thực tế chi tiết...",
    "question": "Câu hỏi nhận diện...",
    "options": ["A. ...", "B. ...", "C. ...", "D. ..."],
    "correct_index": 0,
    "explanation": "Giải thích tại sao đúng từ chân lý gốc...",
    "trap_analysis": "Giải thích bẫy của các phương án sai..."
  }}
]
"""

    for k in keys:
        try:
            genai.configure(api_key=k)
            model = genai.GenerativeModel(model_name=model_name or "gemini-2.5-flash")
            resp = model.generate_content(prompt)
            if resp and resp.text:
                cleaned = re.sub(r"^```[a-zA-Z]*\s*", "", resp.text.strip())
                cleaned = re.sub(r"\s*```$", "", cleaned)
                data = json.loads(cleaned)
                if isinstance(data, list) and len(data) > 0:
                    return data
        except Exception:
            continue
    return None


def evaluate_feynman_challenge(
    api_keys: Union[str, List[str], tuple],
    model_name: str,
    concept_name: str,
    concept_type: str,
    user_explanation: str
) -> Optional[Dict[str, Any]]:
    """Đánh giá bài kiểm tra Feynman: Giải thích nguyên lý phức tạp bằng ngôn ngữ giản dị nhất."""
    keys = _normalize_keys(api_keys)
    if not keys:
        return None

    prompt = f"""Bạn là Giám khảo Kỹ thuật Feynman (Feynman Technique Evaluator).
Khái niệm cần giải thích: {concept_name} ({concept_type})
Lời giải thích của người học:
\"\"\"{user_explanation}\"\"\"

Tiêu chí đánh giá của Richard Feynman:
1. Độ giản dị: Có dùng biệt ngữ học thuật (jargon) để che giấu sự thiếu hiểu biết không? (Học sinh lớp 6 có hiểu được không?)
2. Độ chính xác từ First Principles: Có nắm đúng chân lý bất biến không?
3. Tính sinh động & Ứng dụng: Ví dụ đưa ra có thuyết phục không?

Trả về DUY NHẤT một chuỗi JSON hợp lệ:
{{
  "feynman_score": 8, // Thang điểm từ 1 đến 10
  "verdict": "Xuất sắc / Khá / Còn hàn lâm / Chưa đúng bản chất",
  "praise": "Điểm sáng trong cách giải thích của bạn...",
  "blind_spots": "Lỗ hổng tư duy hoặc điểm bạn đã bỏ sót...",
  "feynman_refinement": "Cách Richard Feynman sẽ giải thích lại khái niệm này trong 2 câu cực kỳ sinh động..."
}}
"""

    for k in keys:
        try:
            genai.configure(api_key=k)
            model = genai.GenerativeModel(model_name=model_name or "gemini-2.5-flash")
            resp = model.generate_content(prompt)
            if resp and resp.text:
                cleaned = re.sub(r"^```[a-zA-Z]*\s*", "", resp.text.strip())
                cleaned = re.sub(r"\s*```$", "", cleaned)
                data = json.loads(cleaned)
                if isinstance(data, dict):
                    return data
        except Exception:
            continue
    return None
