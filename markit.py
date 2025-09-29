# markit_fixed.py
import httpx
import asyncio
import traceback
from typing import Optional

def convert(attendance_id: str) -> str:
    if not isinstance(attendance_id, str) or len(attendance_id) < 6:
        raise ValueError("attendance_id must be a hex string with length >= 6")
    prefix = attendance_id[:-6]
    suffix = attendance_id[-6:].lower()
    try:
        n = int(suffix, 16)
    except ValueError as e:
        raise ValueError("last 6 chars are not valid hex") from e
    n = (n - 1) & 0xFFFFFF
    new_suffix = format(n, "06x")
    return prefix + new_suffix

async def mark_attendance(session_id: str, attendance_id: str, student_id: str,
                          verbose: bool = False, timeout: float = 15.0) -> bool:
    url = "https://student.bennetterp.camu.in/api/Attendance/record-online-attendance"
    headers = {
        "Cookie": f"connect.sid={session_id}",
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "Origin": "https://student.bennetterp.camu.in",
        "Referer": "https://student.bennetterp.camu.in/v2/timetable",
        # include these because the real client had them
        "appversion": "v2",
        "clienttzofst": "330",
    }

    # If attendance_id already contains '_', don't append again
    if "_" in attendance_id:
        payload_attendance = attendance_id
    else:
        try:
            payload_attendance = attendance_id + "_" + convert(attendance_id)
        except Exception as e:
            if verbose:
                print("[ERROR] convert() failed:", e)
            raise

    payload = {
        "attendanceId": payload_attendance,
        "StuID": student_id,
        "offQrCdEnbld": True
    }

    # if verbose:
    #     print("POST", url)
    #     print("HEADERS:", headers)
    #     print("PAYLOAD:", payload)

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, headers=headers, json=payload)
            # if verbose:
            #     print("HTTP", resp.status_code)
            #     print("RESPONSE HEADERS:", dict(resp.headers))
            text = resp.text
            data = None
            try:
                data = resp.json()
            except Exception:
                if verbose:
                    print("[WARN] Non-JSON response:", text[:1000])

            # if verbose:
            #     print("RESPONSE JSON (parsed):", data)

            # Flexible checks:
            if isinstance(data, dict):
                # 1) check existing 'output.data.code' path
                out = data.get("output")
                if out and isinstance(out, dict):
                    out_data = out.get("data")
                    code = None
                    if isinstance(out_data, dict):
                        code = out_data.get("code")
                    # fallback: deep search
                    if not code:
                        def find_code(obj):
                            if isinstance(obj, dict):
                                if "code" in obj:
                                    return obj["code"]
                                for v in obj.values():
                                    r = find_code(v)
                                    if r:
                                        return r
                            if isinstance(obj, list):
                                for it in obj:
                                    r = find_code(it)
                                    if r:
                                        return r
                            return None
                        code = find_code(out_data)
                    if verbose:
                        print("DETECTED CODE:", code)
                    if code in ("SUCCESS", "ATTENDANCE_ALREADY_RECORDED"):
                        return True

                # 2) check more common forms
                top_status = data.get("status") or data.get("statusMessage") or data.get("message") or data.get("result")
                if isinstance(top_status, str):
                    s = top_status.lower()
                    if "success" in s or "ok" in s:
                        return True
                    if "already" in s and "record" in s:
                        return True

                # 3) sometimes API returns boolean flag
                if data.get("marked") is True or data.get("success") is True:
                    return True

            # # if we reached here, consider it a failure
            # if verbose:
            #     print("[INFO] Attendance not marked. Full response:", data or text)
            return False

    except Exception as e:
        if verbose:
            print("[ERROR] exception while sending request:", e)
            traceback.print_exc()
        return False

# Example usage
