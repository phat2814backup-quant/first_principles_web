# Elite Thinking Family — Streamlit Cloud

App tư duy elite dùng chung trong gia đình (≈6 người).

## Tính năng

- Đăng nhập riêng: Phat (admin), Ha, xuka, bong, A1, A2
- Mật khẩu mẫu: `Phat@12345`, `Ha@12345`, `xuka@12345`, `bong@12345`, `A1@12345`, `A2@12345`
- **Knowledge base dùng chung** (`data/knowledge_base.json`)
- **Lịch sử phân rã & tiến độ học tập riêng** từng người (`data/histories/<user>.json`)
- Admin (Phat) xem được tiến độ tất cả mọi người
- Tab **Đào tạo tư duy**: 6 bài lớp 6 + 4 bài lớp 9 (có thể mở rộng / sửa trong Admin)
- Phân rã vấn đề qua elite lenses (Gemini)

## Chạy local

```bash
cd Streamlit
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env   # rồi điền GOOGLE_API_KEY
streamlit run app.py
```

## Deploy Streamlit Community Cloud

1. Đưa thư mục `Streamlit` (hoặc cả repo chứa thư mục này) lên GitHub.
2. Vào [share.streamlit.io](https://share.streamlit.io) → New app.
3. Chọn repo, **Main file path**: `Streamlit/app.py` (hoặc `app.py` nếu root là thư mục Streamlit).
4. **Secrets** (App settings → Secrets):

```toml
GOOGLE_API_KEY = "your_key_here"
```

5. Deploy.

### Lưu ý quan trọng trên Cloud

- File JSON ghi vào `data/histories/` **có thể bị mất khi app reboot** (giới hạn free tier).
- Với 6 người trong gia đình vẫn dùng tốt; nếu cần lưu bền lâu hãy chuyển histories sang Supabase / Google Sheet sau.
- Knowledge base & lessons đọc từ file trong repo → bền.

## Cấu trúc

```
Streamlit/
  app.py
  requirements.txt
  .streamlit/config.toml
  data/
    knowledge_base.json
    lessons.json
    users.json
    histories/          # tạo runtime
  utils/
    auth.py
    knowledge.py
    training.py
    ai_engine.py
```

## Mở rộng sau

- Thêm bài học trong tab Admin
- Đổi mật khẩu trong `data/users.json`
- Thêm user mới trong `users.json`
- Nâng persistence (Supabase) khi cần
