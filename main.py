from fastapi import FastAPI, Request
import mysql.connector
from mysql.connector import Error
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # hoặc cụ thể: ["http://localhost:5500"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class EndSessionRequest(BaseModel):
    session_id: str

@app.post("/end_session")
async def end_session(data: EndSessionRequest):
    mark_session_ended(data.session_id)
    return {"message": "Session ended"}

# Lưu lượt chat vào CSDL
def save_turn(session_id, turn_order, user_query, intent_name, parameters, bot_response):
    try:
        connection = mysql.connector.connect(
            host='localhost',
            database='chatbot_bkacad',
            user='root',
            password=''
        )
        cursor = connection.cursor()

        # Tạo phiên nếu chưa có
        cursor.execute("SELECT session_id FROM chatbot_sessions WHERE session_id = %s", (session_id,))
        if cursor.fetchone() is None:
            cursor.execute("INSERT INTO chatbot_sessions (session_id) VALUES (%s)", (session_id,))

        # Thêm lượt chat
        insert_query = """
                       INSERT INTO chatbot_turns (session_id, turn_order, user_query, intent_name, parameters,
                                                  bot_response)
                       VALUES (%s, %s, %s, %s, %s, %s) \
                       """
        cursor.execute(insert_query, (
            session_id,
            turn_order,
            user_query,
            intent_name,
            str(parameters),
            bot_response
        ))

        connection.commit()

    except Error as e:
        print(f"Lỗi khi lưu lượt chat: {e}")
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()


# Hàm tính số lượt chat hiện tại để đánh số thứ tự
def get_next_turn_order(session_id):
    try:
        connection = mysql.connector.connect(
            host='localhost',
            database='chatbot_bkacad',
            user='root',
            password=''
        )
        cursor = connection.cursor()

        cursor.execute("SELECT COUNT(*) FROM chatbot_turns WHERE session_id = %s", (session_id,))
        count = cursor.fetchone()[0]
        return count + 1

    except Error as e:
        print(f"Lỗi khi lấy số lượt chat: {e}")
        return 1

    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()


def mark_session_ended(session_id):
    try:
        connection = mysql.connector.connect(
            host='localhost',
            database='chatbot_bkacad',
            user='root',
            password=''
        )
        cursor = connection.cursor()

        update_query = "UPDATE chatbot_sessions SET is_ended = TRUE WHERE session_id = %s"
        cursor.execute(update_query, (session_id,))
        connection.commit()

    except Error as e:
        print(f"Lỗi khi đánh dấu kết thúc hội thoại: {e}")
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()


@app.post("/webhook")
async def webhook_handler(request: Request):
    body = await request.json()

    intent_name = body["queryResult"]["intent"]["displayName"]
    session_id = body["session"].split("/")[-1]
    user_query = body["queryResult"].get("queryText", "")
    parameters = body["queryResult"].get("parameters", {})
    response_text = body["queryResult"].get("fulfillmentText", "Xin lỗi, tôi chưa có câu trả lời phù hợp.")

    turn_order = get_next_turn_order(session_id)

    # Lưu lượt chat
    save_turn(session_id, turn_order, user_query, intent_name, parameters, response_text)

    # Nếu là intent kết thúc, đánh dấu session
    if intent_name == "IKetThuc":
        mark_session_ended(session_id)

    return {
        "fulfillmentText": response_text
    }



@app.get("/")
async def root():
    return {"message": "Chatbot API is running"}
