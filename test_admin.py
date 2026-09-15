import sys, json
sys.path.insert(0, ".")
import bot as b
import telebot.types as tt

calls = {"msg": 0, "edit": 0, "answer": 0, "errors": []}

def fake_send(cid, text, **kw):
    calls["msg"] += 1
    o = type("M", (), {"message_id": calls["msg"]})()
    return o

def fake_edit(text, cid, mid, **kw):
    calls["edit"] += 1
    if len(text) < 5:
        calls["errors"].append(f"empty_edit: {repr(text)}")

def fake_answer(cid, text=None, **kw):
    calls["answer"] += 1

b.bot = type("B", (), {
    "send_message": fake_send,
    "edit_message_text": fake_edit,
    "answer_callback_query": fake_answer,
})()
b.set_setting("admin_id", "9999999")

actions = [
    "req", "gift", "giftid", "ref", "channel", "channel_del",
    "paychan", "support", "adv", "stats", "botbal_amount", "botbal", "exit"
]

for act in actions:
    body = {
        "update_id": 1,
        "callback_query": {
            "id": "q_" + act,
            "from": {"id": 9999999, "is_bot": False, "first_name": "A"},
            "message": {
                "message_id": 99,
                "from": {"id": 1, "is_bot": True, "first_name": "b"},
                "chat": {"id": 9999999, "type": "private"},
                "date": 0,
                "text": "panel",
            },
            "chat_instance": "x",
            "data": "set:" + act,
        },
    }
    c = tt.CallbackQuery.de_json(body["callback_query"])
    try:
        b.on_admin_callback(c)
        print("OK:", act)
    except Exception as e:
        print("FAIL:", act, "->", e)
        calls["errors"].append(f"{act}: {e}")

print()
print("msgs:", calls["msg"], "edits:", calls["edit"], "answers:", calls["answer"])
if calls["errors"]:
    print("ERRORS:", calls["errors"])
else:
    print("ALL OK - no errors")
