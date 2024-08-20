import random
import string
import requests
import sys
import json
import concurrent.futures

def makeSerial():
    infix = ["0", "1", "2"]
    upper_alphabet = string.ascii_uppercase
    prefix = ["PF", "MP", "R9", "MJ"]
    postfix = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]
    return random.choice(prefix) + random.choice(infix) + ''.join(random.choices(upper_alphabet, k=4)) + random.choice(postfix)

def getData(serialNumber, machineType):
    url = "https://pcsupport.lenovo.com/us/en/api/v4/upsell/redport/getIbaseInfo"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json"
    }
    data = {
        "serialNumber": serialNumber,
        "machineType": machineType,
        "country": "us",
        "language": "en"
    }
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Failed to get data for {serialNumber}: {e}")
        return None

def getProductData(serialNumber):
    url = f"https://pcsupport.lenovo.com/us/en/api/v4/mse/getproducts?productId={serialNumber}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
        "Accept": "application/json, text/plain, */*"
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Failed to get product data for {serialNumber}: {e}")
        return None

def getTypeFromJson(response_json):
    try:
        id_field = response_json[0]['Name']
        last_type_index = id_field.rfind("Type")
        if last_type_index == -1:
            raise ValueError("No 'Type' field found in 'Name'")
        type_value = id_field[last_type_index:].split()[1].strip()
        return type_value
    except (IndexError, KeyError, AttributeError, ValueError) as e:
        print(f"Error extracting machine type: {e}")
        return None

def process_serial(serial):
    product_response = getProductData(serial)
    output = ""
    
    if product_response and isinstance(product_response, list) and "id" in json.dumps(product_response):
        serial_number = product_response[0]["Serial"]
        machine_type = getTypeFromJson(product_response)
        
        if machine_type:
            data_response = getData(serial_number, machine_type)
            if isinstance(data_response, dict) and data_response.get("data"):
                warranty_info = data_response.get("data", {}).get("baseWarranties", [])
                
                if warranty_info:
                    remaining_days = warranty_info[0].get("remainingDays", 0)
                    if remaining_days > 0:
                        output = f"{serial_number} : {machine_type} - Warranty Active"
                    else:
                        output = f"{serial_number} : {machine_type} - Warranty Expired"
                else:
                    output = f"{serial_number} : {machine_type} - No Warranty Info Available"
            else:
                output = f"{serial_number} : {machine_type} - Failed to retrieve warranty information"
        else:
            output = f"{serial_number} - Machine type extraction failed"
    else:
        output = f"{serial} - Invalid Serial"
    
    return output

def main():
    if len(sys.argv) < 2:
        print("Usage: main.py <serials to generate>")
        sys.exit()
    
    amount = int(sys.argv[1])
    serials = [makeSerial() for _ in range(amount)]
    output_file = "output.txt"

    RED = "\033[91m"
    YELLOW = "\033[93m"
    GREEN = "\033[92m"
    RESET = "\033[0m"

    with open(output_file, 'w') as file_handler:
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_to_serial = {executor.submit(process_serial, serial): serial for serial in serials}
            
            for future in concurrent.futures.as_completed(future_to_serial):
                serial = future_to_serial[future]
                try:
                    result = future.result()
                    file_handler.write(result + '\n')
                    color = GREEN if "Warranty Active" in result else YELLOW if "Warranty Expired" in result else RED
                    print(f"{color}{result}{RESET}")
                except Exception as exc:
                    print(f"Serial {serial} generated an exception: {exc}")

    print(f"Serials saved to {output_file}")

if __name__ == "__main__":
    main()
