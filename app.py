from flask import Flask, request, render_template, jsonify
from datetime import datetime

app = Flask(__name__)

# डेटा सेव करने के लिए 
devices = {}
logs = []
users = []

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/data")
def api_data():
    return jsonify({"devices": devices, "logs": logs, "users": users})

@app.route("/iclock/cdata", methods=["GET", "POST"])
def cdata():
    sn = request.args.get("SN")
    table = request.args.get("table")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if request.method == "GET":
        if sn and sn not in devices:
            devices[sn] = {"sn": sn, "ip": "Online", "first": now, "last": now}
        elif sn:
            devices[sn]["last"] = now

        config_response = (
            f"GET OPTION FROM: SN={sn}\n"
            "Stamp=8000\n"
            "OpStamp=8000\n"
            "ErrorDelay=60\n"
            "Delay=30\n"
            "TransInterval=1\n"
            "TransFlag=1111111111\n"
            "TimeZone=5.5\n"
            "Realtime=1\n"
            "Encrypt=0\n"
            "OK"
        )
        return config_response, 200, {'Content-Type': 'text/plain'}

    if request.method == "POST":
        raw_payload = request.get_data(as_text=True).strip()
        
        if sn and sn not in devices:
            devices[sn] = {"sn": sn, "ip": "Online", "first": now, "last": now}
        elif sn:
            devices[sn]["last"] = now

        if raw_payload:
            for line in raw_payload.splitlines():
                if not line.strip():
                    continue
                
                entry = {"sn": sn if sn else "UNKNOWN", "data": line.strip(), "time": now}
                if table == "ATTLOG" or "USERID=" in line:
                    logs.insert(0, entry)
                    if len(logs) > 200: logs.pop()
                elif table == "USER":
                    users.insert(0, entry)
                    if len(users) > 200: users.pop()

        return "OK", 200, {'Content-Type': 'text/plain'}

@app.route("/iclock/getrequest", methods=["GET"])
def getrequest():
    sn = request.args.get("SN")
    if sn in devices:
        devices[sn]["last"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return "OK", 200, {'Content-Type': 'text/plain'}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)