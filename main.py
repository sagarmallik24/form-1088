from flask import Flask, request, jsonify
import requests
import json
import config
from gevent.pywsgi import WSGIServer
from flask_cors import CORS, cross_origin
from helpers.g_sheet_handler import GoogleSheetHandler
from datetime import datetime
from requests.exceptions import RequestException
from urllib.parse import unquote

app = Flask(__name__)
CORS(app)


@app.route('/', methods=['GET','POST'])
@cross_origin(origin='*')
def execute():
    if request.method == 'GET':
        date = datetime.now()
        e = request.args.to_dict()

        #Logging data into sheet
        RequestValue = str(request.query_string, 'utf-8')
        customResponse = [[date.strftime("%d/%m/%Y, %H:%M:%S"), 'GET', RequestValue]]
        GoogleSheetHandler(data = customResponse, sheet_name=config.SHEET_USER_DATA_LOG, spreadsheet_id=config.SAMPLE_SPREADSHEET_ID_FSP).appendsheet_records()
        print(" ============================== Data Logged Successfully ==================================  ")
        response = ""

        if e.get('action') == "getStudentDetails":
            lang_type = "Darkon" if e.get('country_code') else None

            if e.get('CheckPhoneCode') and (e.get('CheckPhoneCode') != "undefined"):

                phone_code_res = validate_phone_code(e['Phone'], e['CheckPhoneCode'], lang_type)
            
                if not phone_code_res['CheckPhoneCodeStatus']:
                    return jsonify(phone_code_res)

                duplicate_check_res = check_duplicate_student_id(e['studentId'], lang_type)
                duplicate_check_res = json.loads(duplicate_check_res)
                
                if 'DuplicateVerification' in duplicate_check_res and duplicate_check_res['DuplicateVerification']:
                    return jsonify(duplicate_check_res)

                success_json = {"message": "Successfully Completed."}
                return jsonify(success_json)

            if e.get('country_code') and (e.get('country_code') != 'undefined'):
                response = verify_passport(e['country_code'], e['studentId'])
                if response.get('error'):
                    print("Error While Verify The Passport..")
                    return jsonify(response)

                if response.get('data') is False:
                    return jsonify(response)

            student_res = find_student_new(e['groupId'], e['Phone'], e.get('CheckPhoneCode'), lang_type)
            print("Student Res =>", student_res)

            if not student_res['CheckPhoneCodeStatus'] or not student_res['groupStatus']:
                return jsonify(student_res)

            success_json = {"message": "Successfully Completed."}
            return jsonify(success_json)

        return jsonify({"error": "Invalid endpoint!"})
    
    elif request.method == "POST":
        incoming_data = request.data.decode('utf-8')
        decoded_string = unquote(incoming_data, encoding='utf-8')

        formData = json.loads(decoded_string)
        print("FormData =>",formData)
        phone_code_res = validate_phone_code(formData['Tel1'], formData['CheckPhoneCode'], formData['Zihuy'])
        print("verify code response =>", phone_code_res)

        if not phone_code_res['CheckPhoneCodeStatus']:
            return jsonify(phone_code_res)
        
        if formData['Snif'] != "" and formData['Bank'] != "":
            # Verify bank details
            bankResponse = verify_bank_details(formData['Bank'],formData['Snif'],formData['Account'])
            print("Bank Response =>", bankResponse)

            if bankResponse['error']:
                response_output = json.dumps(bankResponse)
                return response_output
            elif not bankResponse['data']:
                tmp = json.dumps(bankResponse)
                return tmp
        
        try:
            group_res = find_group_details_sutra(formData, "1wfwhswUI573zWG6Xu7HxtpaFJ7p9MIsy9Gz0HfdTT6A", "V2", "J")
            group_res = group_res
            if group_res['status'] == 'failed':
                group_res = find_group_details_sutra(formData, "1wfwhswUI573zWG6Xu7HxtpaFJ7p9MIsy9Gz0HfdTT6A", "GRUPS", "M")
                if group_res['status'] == 'failed':
                    parse_response(formData, "failed", group_res)
                else:
                    parse_response(formData, "גיליון1", group_res)
            else:
                parse_response(formData, "גיליון1", group_res)
        except Exception as e:
            log_error(str(e))
            

        return {"response":"SUCCESS"}
        # customValue = dict(formData)
        # customResponse = [[str(date.strftime("%d/%m/%Y, %H:%M:%S")), 'POST',
        #                     str(customValue)]]
        # GoogleSheetHandler(data = customResponse, sheet_name=config.SHEET_USER_DATA_FSP, spreadsheet_id=config.SAMPLE_SPREADSHEET_ID_FSP).appendsheet_records()



def log_request(e):
    # Log the request details (replace with your logging mechanism)
    print("-----------------------------------")
    print("LOG Request =>", e)
    print("-----------------------------------")

def log_error(e):
    # Log the request details (replace with your logging mechanism)
    print("-----------------------------------")
    print("LOG ERROR =>", e)
    print("-----------------------------------")


def verify_passport(country_code, passport_id):
    url = "https://schoolmanager.services/passport_id_validation"
    body = {
        "country_code": country_code,
        "passport_id": passport_id,
        "api_password": "fkhjas907412zxcl,nja7$%!#!"
    }
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    options = {
        "headers": headers,
        "json": body,
        "verify": False  # Set this to True to enable SSL certificate verification
    }

    response = requests.post(url, **options)
    return response.json()

def verify_bank_details(bank, snif, account):
    print("From Verify bank details=>", bank, snif, account)
    url = "https://schoolmanager.services/bank_account_validation"
    body = {
        "bank_inspection": {
            "Bank": bank,
            "Snif": snif,
            "Account": account
            },
        "api_password": "fkhjas907412zxcl,nja7$%!#!"
    }

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    options = {
        "headers": headers,
        "json": body,
        "verify": False  # Set this to True to enable SSL certificate verification
    }

    response = requests.post(url, **options)
    return response.json()


def validate_phone_code(phone_number, check_phone_code, lang_type):

    # Replace with your actual implementation
    sheet_data = GoogleSheetHandler(sheet_name=config.SHEET_CODE_STORAGE, spreadsheet_id=config.SHEET_1088_ID).getsheet_records()
    json_heb = {"CheckPhoneCodeStatus": False, "message": "הקוד שהזנת אינו תואם נסה שוב"}
    json_eng = {"CheckPhoneCodeStatus": False, "message": "The code you entered does not match. Try again"}


    if phone_number and check_phone_code:
        filtered_data = [(item[2], item[3]) for item in sheet_data][1:]
        data = list(reversed(filtered_data))

        index = -1
        for i, (ph, _) in enumerate(data):
            if int(ph) == int(phone_number[1:]):
                index = i
                print("----------------- MATCHED PHONE -------------- ")
                break


        if index != -1:
            code = data[index][1]
            
            if int(code) == int(check_phone_code):
                print("----------------- MATCHED OTP -------------- ")

                json_heb["CheckPhoneCodeStatus"] = True
                json_heb["message"] = "האימות עבר בהצלחה!"

                json_eng["CheckPhoneCodeStatus"] = True
                json_eng["message"] = "Verification passed successfully!"

            else:
                print("----------------- DIDN'T MATCHED CODE -------------- ")
                json_heb["message"] = 'הקוד שהזנת אינו תואם נסה שוב'
                json_eng["message"] = 'The code you entered does not match Try again'

        else:
            json_heb["message"] = 'הקוד שהזנת אינו תואם נסה שוב'
            json_eng["message"] = "The code you entered does not match. Try again"

    return json_heb if lang_type == "Darkon" else json_eng


def find_group_details_sutra(response, SSID, TabName, Column):
    log_data = response
    print("From details sutra")

    code_kolel_boker = log_data['CodKolelBoker']
    code_kolel_zarim = log_data['CodKolelZarim']

    json_heb = {
        "status": "succeeded",
        "message": "אברך יקר הטופס נשלח בהצלחה",
        "content": {"CodKolelBoker": False, "CodKolelZarim": False}
    }

    json_eng = {
        "status": "succeeded",
        "message": "Dear Avrach, the form has been sent successfully",
        "content": {"CodKolelBoker": False, "CodKolelZarim": False}
    }

    if code_kolel_boker is None or code_kolel_boker == '':
        del json_heb['content']['CodKolelBoker']
        del json_eng['content']['CodKolelBoker']
    else:
        code_kolel_boker = str(code_kolel_boker)

    if code_kolel_zarim is None or code_kolel_zarim == '':
        del json_heb['content']['CodKolelZarim']
        del json_eng['content']['CodKolelZarim']
    else:
        code_kolel_zarim = str(code_kolel_zarim)

    try:

        group_data = GoogleSheetHandler(sheet_name=TabName, spreadsheet_id=SSID).getsheet_records_with_range(range=f"{TabName}!{Column}2:{Column}")

        code = []
        for item in group_data:
            if len(item)>=1:
                if item[0] != '':
                    code.append(str(item[0]))
        boker_code_index = code.index(code_kolel_boker) if code_kolel_boker in code else -1
        zarim_code_index = code.index(code_kolel_zarim) if code_kolel_zarim in code else -1


        if boker_code_index >= 0:
            json_eng['status'] = "succeeded"
            json_heb['status'] = "succeeded"
            if zarim_code_index >= 0:
                json_eng['message'] = "Dear Avrach, the form has been sent successfully"
                json_heb['message'] = "אברך יקר הטופס נשלח בהצלחה"
                json_eng['content']['CodKolelBoker'] = True
                json_heb['content']['CodKolelBoker'] = True
                json_eng['content']['CodKolelZarim'] = True
                json_heb['content']['CodKolelZarim'] = True
            else:
                json_eng['message'] = "Dear Avrach, the form has been sent successfully"
                json_heb['message'] = "אברך יקר הטופס נשלח בהצלחה"
                json_eng['content']['CodKolelBoker'] = True
                json_heb['content']['CodKolelBoker'] = True
        elif zarim_code_index >= 0:
            json_eng['status'] = "succeeded"
            json_eng['message'] = "Dear Avrach, the form has been sent successfully"
            json_heb['status'] = "succeeded"
            json_heb['message'] = "אברך יקר הטופס נשלח בהצלחה"
            json_eng['content']['CodKolelZarim'] = True
            json_heb['content']['CodKolelZarim'] = True
        else:
            json_heb['status'] = "failed"
            json_heb['message'] = "שליחת הטופס נכשלה קוד כולל בוקר שגוי /קוד כולל צהריים שגוי נא לפנות לאחראי בכולל"
            json_eng['status'] = "failed"
            json_eng['message'] = "Sending the form failed. Incorrect morning total code / Incorrect afternoon total code. Please contact the person in charge at Kollel"

        if log_data['Zihuy'] == "Passport":
            print(json_eng)
            print("---------------------- 1")
            return json_eng
        print(json_heb)
        print("------------------2")
        return json_heb
    except Exception as e:
        print("Exeption is find_group_details_sutra ----- ",str(e))

        return jsonify({"error": "Some Error Occurred While Getting the Response"})

def parse_response(formData, sheet_name, group_res, sheet=None):
    print("Parse response")
    json_data = formData

    row = []

    if sheet is None:
        group_data = GoogleSheetHandler(sheet_name=sheet_name, spreadsheet_id='1S8QOS8uEw8aIS27ekyOCaHLShYL1T6d17U-frj_2YRs').getsheet_records()
        print("Group data  from sheet =>", group_data)
    # last_row = sheet.row_count

    # row.append([last_row + 1, str(datetime.datetime.now()), '', '',
    row.append(["last_row+" + "1", str(datetime.now()), '', '',
            json_data.get('FirstName', ''),
            json_data.get('Family', ''),
            json_data.get('Tel1', ''),
            json_data.get('Tel2', ''),
            json_data.get('Tel3', ''),
            json_data.get('City', ''),
            json_data.get('Street', ''),
            json_data.get('StreetNum', ''),
            json_data.get('BDE', ''),
            json_data.get('Isdichuy', ''),
            json_data.get('Zihuy', ''),
            json_data.get('Zeout', ''),
            json_data.get('Darkon', ''),
            json_data.get('countryDarkon', ''),
            json_data.get('Isvisa', ''),
            json_data.get('Bank', ''),
            json_data.get('Snif', ''),
            json_data.get('Account', ''),
            json_data.get('IsMail', ''),
            json_data.get('Mail', ''),
            json_data.get('DayDatot', ''),
            json_data.get('NameKolelMorning', ''),
            json_data.get('TelKolelMorning', ''),
            json_data.get('NameKolelNoon', ''),
            json_data.get('TelKolelNoon', ''),
            json_data.get('Lomedbkolel', ''),
            "",  # Remove field LomedbkolelAPlace
            json_data.get('KolelKodem', ''),
            json_data.get('IsTlush', ''),
            json_data.get('NameMosad1', ''),
            json_data.get('TypeMosad1', ''),
            json_data.get('GovaTlush1', ''),
            json_data.get('Numtime1', ''),
            json_data.get('Ishur', ''),
            json_data.get('IsMslullimudim', ''),
            json_data.get('NameMosad2', ''),
            json_data.get('Numtime2', ''),
            json_data.get('Ishur2', ''),
            json_data.get('IsShrutLumi', ''),
            json_data.get('NumTypeMdvech', ''),
            json_data.get('timeDivuch', ''),
            json_data.get('Ishur5', ''),
            json_data.get('Ishur6', ''),
            json_data.get('Ishur7', ''),
            json_data.get('CodKolelBoker', ''),
            json_data.get('CodKolelZarim', ''),
            json_data.get('BetNoon', ''),
            json_data.get('BetMorning', ''),
            json_data.get('TypeKolelMorning', ''),
            json_data.get('ThereIsNoBankAccountInIsrael', ''),
            json_data.get('IsCityMorning', ''),
            json_data.get('LomedkolelMorning', ''),
            json_data.get('IsukkolelMorning', ''),
            json_data.get('IsTheCellPhoneAvailableMorning', ''),
            json_data.get('IsThereReceptionMorning', ''),
            json_data.get('TypeKolelNoon', ''),
            json_data.get('IsCityNoon', ''),
            json_data.get('LomedkolelNoon', ''),
            json_data.get('IsukkolelNoon', ''),
            json_data.get('IsTheCellPhoneAvailableNoon', ''),
            json_data.get('IsThereReceptionNoon', ''),
            json_data.get('AreYouPlanningUToLeaveTheCountry', ''),
            json_data.get('AreYouPlanningUToLeaveTheCountryYasFlightDate', ''),
            json_data.get('AreYouPlanningUToLeaveTheCountryYasReturnDate', ''),
            json_data.get('DoYouPlanToLeaveTheCountryBeforeTheEndOfTime', ''),
            json_data.get('DoYouPlanToLeaveTheCountryBeforeTheEndOfTimeYasFlightDate', ''),
            json_data.get('DoYouPlanToLeaveTheCountryBeforeTheEndOfTimeYasReturnDate', ''),
            "",
            ])

    row[0].append(json.dumps(group_res))

    row[0].extend([
        json_data.get('ZavaNameAv', ''),
        json_data.get('PassportExpiration', ''),
        json_data.get('NumKids', ''),
        json_data.get('ColumnNumberMorning', ''),
        json_data.get('LineNumberMorning', ''),
        json_data.get('TheNameOfTheGroupMorning', ''),
        json_data.get('ColumnNumberNoon', ''),
        json_data.get('LineNumberNoon', ''),
        json_data.get('TheNameOfTheGroupNoon', ''),
        json_data.get('RegistrationLocation', ''),
        json_data.get('LineNumberNoon', ''),
        json_data.get('TheNameOfTheGroupNoon', ''),
        json_data.get('RegistrationLocation', ''),
        json_data.get('RegistersName', ''),
        json_data.get('ErrorDescribe', ''),
        json_data.get('PhoneVerification', ''),
        json_data.get('TheNameOfTheGroupMorning', ''),
        json_data.get('ColumnNumberNoon', ''),
        json_data.get('LineNumberNoon', ''),
        json_data.get('TheNameOfTheGroupNoon', ''),
        json_data.get('RegistrationLocation', ''),
        json_data.get('registersName', ''),
        json_data.get('errorDescribe', ''),
        json_data.get('phoneVerification', '')
    ])

    # Convert all values to strings
    row = [str(value) for value in row[0]]
    Data = [row]

    group_data = GoogleSheetHandler(data = Data, sheet_name=sheet_name, spreadsheet_id='1S8QOS8uEw8aIS27ekyOCaHLShYL1T6d17U-frj_2YRs').appendsheet_records()
                        
    return jsonify({"message": "Success"}), 200


def find_student_new(group_id, phone_number, check_phone_code, lang_type):
    date = datetime.now()
    print("+++++++++++++++++++++++++++++")
    print(group_id, check_phone_code, phone_number)
    print("------------------------------")
    # Replace with your actual implementation
    group_data = GoogleSheetHandler(sheet_name=config.SHEET_V2, spreadsheet_id=config.SAMPLE_SPREADSHEET_ID).getsheet_records_with_range(range="V2!J2:J")
    
    student_data = GoogleSheetHandler(sheet_name=config.SHEET_GRUPS, spreadsheet_id=config.SAMPLE_SPREADSHEET_ID).getsheet_records_with_range(range="GRUPS!M4:M")


    json_heb = {"status": "failed", "groupStatus": False, "message": "הקוד הכולל שהזנת אינו תקין תשאל את האחראי !", "CheckPhoneCodeStatus": False}
    json_eng = {"status": "failed", "groupStatus": False, "message": "The code kolell you entered is incorrect, ask the manager !", "CheckPhoneCodeStatus": False}

    try:
        group_index1 = None

        for i, item in enumerate(group_data):
            if item and item[0] == group_id:
                group_index1 = i
                print("MATCHEDDDDD +++++++++++++++++++++++++++++++++++++++ 1")
                break

    except StopIteration:
        group_index1 = -1

    try:
        group_index2 = None

        for i, item in enumerate(student_data):
            if item and item[0] == group_id:
                print("MATCHEDDDDD +++++++++++++++++++++++++++++++++++++++ 2")
                group_index2 = i
                break

        print(group_index2, "Group index 2")

    except StopIteration:
        group_index2 = -1

    print(group_index1, group_index2)
    if group_index1 == None and group_index2 == None:
        print("Group Id not found in both the sources..")
        return json_eng if lang_type == "Darkon" else json_heb

    json_heb["groupStatus"] = True
    json_eng["groupStatus"] = True

    sheet_data = []  # Replace with actual data from your sheet
    if phone_number and check_phone_code is None and json_eng["groupStatus"]:
        print("First Click for Send OTP")

        code_url = f"https://www.call2all.co.il/ym/api/RunTzintuk?token=0794690474:7974153&callerId=RAND&phones={phone_number}"
        res = requests.get(code_url).json()
        print("Code URL", code_url)

        json_heb["CheckPhoneCodeStatus"] = True
        json_heb["message"] = "מספר הטלפון שהזנת נכון"

        json_eng["CheckPhoneCodeStatus"] = True
        json_eng["message"] = "The phone number you entered is correct"

        if res["responseStatus"] == 'Exception':
            json_heb["CheckPhoneCodeStatus"] = False
            json_heb["message"] = 'אתם חסומים לצינתוקים-להסרת החסימה תשלחו מייל cs@yemot.co.il'

            json_eng["CheckPhoneCodeStatus"] = False
            json_eng["message"] = "אתם חסומים לצינתוקים-להסרת החסימה תשלחו מייל cs@yemot.co.il,The phone number you entered is incorrect !"

        try:
            verify_code = res["verifyCode"]
        except KeyError:
            verify_code = ""
        print("VERIFY CODE", verify_code)
        data_append = [[date.strftime("%d/%m/%Y %H:%M:%S"),str(res['responseStatus']),int(phone_number),str(verify_code),str(res)]]
        print("DATA TO APPEND =>", data_append)
        code_storage = GoogleSheetHandler(data = data_append, sheet_name=config.SHEET_CODE_STORAGE,
                                            spreadsheet_id=config.SHEET_1088_ID).appendsheet_records()
        print("Code Storage =>", code_storage)
    return json_eng if lang_type == "Darkon" else json_heb


def check_duplicate_student_id(student_id, lang_type):
    # Replace with your actual implementation
    if student_id is None:
        student_id = "324150838"

    duplicate_json_eng = {"DuplicateVerification": False, "CheckPhoneCodeStatus": True}
    duplicate_json_heb = {"DuplicateVerification": False, "CheckPhoneCodeStatus": True}

    try:
        data = GoogleSheetHandler(sheet_name=config.CHECK_DUPLICATE_SHEET, spreadsheet_id=config.SAMPLE_SPREADSHEET_ID_FOR_DUPLICATE_STUDENT).getsheet_records()
    except IndexError:
        print("Data not found")
        return

    index = -1
    for i, item in enumerate(data):
        try:
            if item[15] == str(student_id) or item[16] == str(student_id):
                index = i
                break
        except IndexError:
            pass  # Handle the IndexError silently and continue to the next iteration

    print("INDEX =>", index)

    if index != -1:
        duplicate_json_eng["DuplicateVerification"] = True
        duplicate_json_heb["DuplicateVerification"] = True

        code_kolel_boker = data[index][48]
        code_kolel_zarim = data[index][49]

        if code_kolel_boker and code_kolel_zarim:
            duplicate_json_eng["data"] = {
                "CodKolelBoker": code_kolel_boker,
                "CodKolelZarim": code_kolel_zarim,
            }

            duplicate_json_heb["data"] = {
                "CodKolelBoker": code_kolel_boker,
                "CodKolelZarim": code_kolel_zarim,
            }

            duplicate_json_eng["message"] = (
                f"You have already requested to register for morning with code {code_kolel_boker} "
                f"and afternoon with code {code_kolel_zarim}. Ask the manager"
            )
            duplicate_json_heb["message"] = (
                f"כבר ביקשת להירשם לבוקר עם קוד {code_kolel_boker} ואחר הצהריים עם קוד {code_kolel_zarim} תשאל את המנהל"
            )

        elif code_kolel_boker and not code_kolel_zarim:
            duplicate_json_eng["data"] = {"CodKolelBoker": code_kolel_boker}
            duplicate_json_heb["data"] = {"CodKolelBoker": code_kolel_boker}
            duplicate_json_eng["message"] = (
                f"You have already requested to register for morning with code {code_kolel_boker}. Ask the manager"
            )
            duplicate_json_heb["message"] = (
                f"כבר ביקשת להירשם בוקר עם קוד {code_kolel_boker} שאל את המנהל"
            )

        elif not code_kolel_boker and code_kolel_zarim:
            duplicate_json_eng["data"] = {"CodKolelZarim": code_kolel_zarim}
            duplicate_json_heb["data"] = {"CodKolelZarim": code_kolel_zarim}
            duplicate_json_eng["message"] = (
                f"You have already requested to register for afternoon with code {code_kolel_zarim}. Ask the manager"
            )
            duplicate_json_heb["message"] = (
                f"כבר ביקשת להירשם לשעות אחר הצהריים עם קוד {code_kolel_zarim} תשאל את המנהל"
            )

    if duplicate_json_eng["DuplicateVerification"] == True:
        duplicate_json_eng["status"] = "failed"
        duplicate_json_heb["status"] = "failed"

    if lang_type == "Darkon":
        return json.dumps(duplicate_json_eng)

    return json.dumps(duplicate_json_heb)
    

if __name__=='__main__':
    app.run(host='0.0.0.0', port=1088, debug=True)
    # app.run(ssl_context=('cert.pem','key.pem'))
    # http_server = WSGIServer(('74.208.188.36', 5000), app)
    # http_server.serve_forever()
