import requests
from datetime import datetime

from sid import *

def fetch_timetable_headerless(sid, json_payload):
    api_url = "https://student.bennetterp.camu.in/api/Timetable/get"
    cookies = {
        "connect.sid": sid
    }

    now=datetime.now()

    json_payload.update({
        "enableV2": True,
        "start": now.strftime("%Y-%m-%d"),
        "end": now.strftime("%Y-%m-%d"),
        "usrTime": now.strftime("%d-%m-%Y, %I:%M %p"),
        "schdlTyp": "slctdSchdl",
        "isShowCancelledPeriod": True,
        "isFromTt": True
    })
    
    try:
        response = requests.post(api_url, cookies=cookies, json=json_payload)

        # Check if the response status code indicates success
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error: Received status code {response.status_code}")
            # print(response.json())
            return None
    except requests.RequestException as e:
        print(f"Request failed: {e}")
        # print(response.json())
        return None

# with open('user_data.json','r') as f:
    # data = json.load(f)
    # sid = data['sid']
    # json_payload = data['data']['progressionData'][0]

    # raw_data = fetch_timetable_headerless(sid,json_payload)
        
    # def parse_timetable(raw):
    #     periods = raw['output']['data'][0]['Periods']
    #     timetable = []

    #     for p in periods:
    #         timetable.append({
    #             "Start": datetime.fromisoformat(p['start']).strftime("%H:%M"),
    #             "End": datetime.fromisoformat(p['end']).strftime("%H:%M"),
    #             "Subject": p['SubNa'],
    #             "Staff": p['StaffNm'],
    #             "Location": p['Location'],
    #             "AttendanceSaved": p.get('isAttendanceSaved', False)
    #         })

    #     return timetable

    # clean_tt = parse_timetable(raw_data)

    # # Pretty print
    # for period in clean_tt:
    #     print(f"{period['Start']} - {period['End']}: {period['Subject']} with {period['Staff']} at {period['Location']}, Attendance Saved: {period['AttendanceSaved']}")