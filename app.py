from flask import Flask, request, render_template, jsonify
from datetime import datetime

app = Flask(__name__)

# डेटा सेव करने के लिए
devices = {}
logs = []
users = {}            # PIN -> {pin, name, card, time}

pending_cmds = {}     # SN -> [command strings device को भेजने हैं]
_cmd_id = [0]         # unique command counter


def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def touch_device(sn, ip=None):
    now = now_str()
    if sn and sn not in devices:
        devices[sn] = {"sn": sn, "ip": ip or "Online", "first": now, "last": now}
    elif sn:
        devices[sn]["last"] = now


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/data")
def api_data():
    # users dict -> list (नए ऊपर)
    user_list = sorted(users.values(), key=lambda u: u["time"], reverse=True)
    return jsonify({"devices": devices, "logs": logs, "users": user_list})


@app.route("/api/fetch_users", methods=["POST"])
def fetch_users():
    """हर connected device को 'सारे users भेजो' command queue करता है।"""
    target = request.args.get("SN")
    targets = [target] if target else list(devices.keys())
    if not targets:
        return jsonify({"ok": False, "msg": "koi device connected nahi"}), 400

    for sn in targets:
        _cmd_id[0] += 1
        cmd = f"C:{_cmd_id[0]}:DATA QUERY USERINFO"
        pending_cmds.setdefault(sn, []).append(cmd)

    return jsonify({"ok": True, "msg": f"{len(targets)} device(s) ko command bhej diya, thodi der me users aa jayenge", "devices": targets})


@app.route("/api/fetch_logs", methods=["POST"])
def fetch_logs():
    """हर device को पुरानी सारी attendance (ATTLOG) भेजने का command queue करता है।"""
    target = request.args.get("SN")
    targets = [target] if target else list(devices.keys())
    if not targets:
        return jsonify({"ok": False, "msg": "koi device connected nahi"}), 400

    start = "2000-01-01 00:00:00"
    end = "2037-12-31 23:59:59"
    for sn in targets:
        _cmd_id[0] += 1
        cmd = f"C:{_cmd_id[0]}:DATA QUERY ATTLOG StartTime={start}\tEndTime={end}"
        pending_cmds.setdefault(sn, []).append(cmd)

    return jsonify({"ok": True, "msg": f"{len(targets)} device(s) ko purana data command bhej diya, thodi der me aayega", "devices": targets})


@app.route("/iclock/cdata", methods=["GET", "POST"])
def cdata():
    sn = request.args.get("SN")
    table = request.args.get("table")
    now = now_str()

    if request.method == "GET":
        touch_device(sn)
        config_response = (
            f"GET OPTION FROM: SN={sn}\n"
            "Stamp=8000\n"
            "OpStamp=8000\n"
            "ErrorDelay=60\n"
            "Delay=10\n"
            "TransInterval=1\n"
            "TransFlag=1111111111\n"
            "TimeZone=5.5\n"
            "Realtime=1\n"
            "Encrypt=0\n"
            "OK"
        )
        return config_response, 200, {'Content-Type': 'text/plain'}

    # POST
    raw_payload = request.get_data(as_text=True).strip()
    touch_device(sn)

    if raw_payload:
        for line in raw_payload.splitlines():
            line = line.strip()
            if not line:
                continue

            # ---- USER record (naam ke saath) ----
            if line.startswith("USER PIN="):
                body = line[len("USER "):]          # "PIN=8\tName=Ahmed\t..."
                data = {}
                for f in body.split("\t"):
                    if "=" in f:
                        k, v = f.split("=", 1)
                        data[k.strip()] = v.strip()
                pin = data.get("PIN")
                if pin:
                    users[pin] = {
                        "pin": pin,
                        "name": data.get("Name", "") or "(no name)",
                        "card": data.get("Card", ""),
                        "time": now,
                    }
                continue

            # ---- Attendance / baaki logs ----
            entry = {"sn": sn if sn else "UNKNOWN", "data": line, "time": now}
            logs.insert(0, entry)
            if len(logs) > 10000:
                logs.pop()

    return "OK", 200, {'Content-Type': 'text/plain'}


@app.route("/iclock/getrequest", methods=["GET"])
def getrequest():
    sn = request.args.get("SN")
    touch_device(sn)

    # koi pending command ho to device ko de do
    queue = pending_cmds.get(sn)
    if queue:
        cmd = queue.pop(0)
        return cmd + "\n", 200, {'Content-Type': 'text/plain'}

    return "OK", 200, {'Content-Type': 'text/plain'}


@app.route("/iclock/devicecmd", methods=["GET", "POST"])
def devicecmd():
    """device command ka result yaha bhejta hai — bas OK karna hai."""
    sn = request.args.get("SN")
    touch_device(sn)
    return "OK", 200, {'Content-Type': 'text/plain'}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
