# markit.py
import httpx
import traceback
from typing import Optional


def convert(attendance_id: str) -> str:
    """
    Given a hex attendance_id string, decrement the last 6 hex digits by 1
    (with wrap-around) and return the full new hex string.

    Example:
      convert("68cbba402609574c0ea2f54e")
      -> "68cbba402609574c0ea2f54d"
    """
    if not isinstance(attendance_id, str) or len(attendance_id) < 6:
        raise ValueError("attendance_id must be a hex string with length >= 6")

    prefix = attendance_id[:-6]
    suffix = attendance_id[-6:]

    # normalize
    suffix = suffix.lower()

    # parse hex to int
    try:
        n = int(suffix, 16)
    except ValueError as e:
        raise ValueError("last 6 chars are not valid hex") from e

    # subtract 1 with wrap-around modulo 2^24 (so -0 -> 0xFFFFFF)
    n = (n - 1) & 0xFFFFFF

    # format back to 6-digit hex (zero-padded, lowercase)
    new_suffix = format(n, '06x')

    return prefix + new_suffix

async def mark_attendance(session_id: str, attendance_id: str, student_id: str, verbose: bool = False) -> bool:
    """
    Mark attendance using the given session cookie.

    Parameters:
      - session_id: connect.sid cookie value (string)
      - attendance_id: attendance identifier
      - student_id: student id / StuID
      - verbose: if True, prints detailed request/response debugging info

    Returns:
      - True if server responded with SUCCESS or ATTENDANCE_ALREADY_RECORDED
      - False otherwise (including network errors)
    """
    url = "https://student.bennetterp.camu.in/api/Attendance/record-online-attendance"
    headers = {
        "Cookie": f"connect.sid={session_id}",
        "User-Agent": "Mozilla/5.0" ,
        "Accept": "application/json, text/plain, /",
        "Content-Type": "application/json",
        "Origin": "https://student.bennetterp.camu.in",
        "Referer": "https://student.bennetterp.camu.in/v2/timetable",
    }
    payload = {
        "attendanceId": attendance_id+"_"+convert(attendance_id),
        # "isMeetingStarted": True,
        "StuID": student_id,
        "offQrCdEnbld": True
    }

    # print(payload["attendanceId"])

    if verbose:
        print("\n--- MARK ATTENDANCE REQUEST ---")
        print("URL:", url)
        print("HEADERS:", headers)
        print("PAYLOAD:", payload)
        print("------------------------------\n")

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(url, headers=headers, json=payload)

            status = response.status_code
            text = response.text
            resp_headers = dict(response.headers)

            if verbose:
                print("\n--- RESPONSE RECEIVED ---")
                print("STATUS:", status)
                print("RESPONSE HEADERS:", resp_headers)
                # limit long responses to avoid flooding terminal but show enough
                display_text = text if len(text) < 10000 else text[:10000] + "\n...[truncated]"
                print("RESPONSE TEXT:", display_text)
                print("-------------------------\n")

            # Try to parse JSON 
            data = None
            try:
                data = response.json()
            except Exception:
                if verbose:
                    print("[WARN] Response is not valid JSON (or JSON parsing failed).")

            if verbose:
                print("PARSED JSON:", data)

            # Old code expected data["output"]["data"]["code"]
            try:
                if data and isinstance(data, dict):
                    out = data.get("output")
                    if out is None:
                        if verbose:
                            print("[INFO] No 'output' field in response.")
                        return False

                    out_data = out.get("data")
                    # If out_data is None or not present, print diagnostic info
                    if out_data is None:
                        if verbose:
                            print("[INFO] 'output.data' is None. Full output:", out)
                        return False

                    # If code present, evaluate result
                    code = None
                    if isinstance(out_data, dict):
                        code = out_data.get("code")
                    # Some responses may return the code at a different nested location
                    if not code:
                        # attempt to find code by scanning dict (last resort)
                        def find_code(obj):
                            if isinstance(obj, dict):
                                if "code" in obj:
                                    return obj["code"]
                                for v in obj.values():
                                    res = find_code(v)
                                    if res:
                                        return res
                            if isinstance(obj, list):
                                for item in obj:
                                    res = find_code(item)
                                    if res:
                                        return res
                            return None
                        code = find_code(out_data)

                    if verbose:
                        print("DETECTED CODE:", code)

                    if code in ["SUCCESS", "ATTENDANCE_ALREADY_RECORDED"]:
                        return True
                    else:
                        # Print server-provided status message if available
                        if verbose:
                            msg = out.get("statusMessage") if isinstance(out, dict) else None
                            print(f"[INFO] Attendance not marked. Server code: {code}, statusMessage: {msg}")
                        return False
                else:
                    if verbose:
                        print("[INFO] Unexpected response structure:", type(data))
                    return False
            except Exception as e:
                if verbose:
                    print("[ERROR] while interpreting response:", e)
                    traceback.print_exc()
                return False

    except Exception as e:
        if verbose:
            print("[ERROR] Exception occurred while sending request:", e)
            traceback.print_exc()
        return False