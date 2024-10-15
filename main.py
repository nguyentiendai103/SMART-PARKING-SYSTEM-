import tkinter as tk
from tkinter import messagebox, filedialog
from tkinter.ttk import *
from PIL import Image, ImageTk
import cv2
import threading
import time
import numpy as np
import imutils
import math
import serial
import pytesseract
import os
import pypyodbc as odbc
import datetime


# Thiết lập đường dẫn tới tesseract.exe
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Khởi tạo cổng Serial
DataSerial = serial.Serial('COM5', 9600)
time.sleep(1)

# Khởi tạo cửa sổ Tkinter
root = tk.Tk()
root.title("Phần mềm nhận diện xe")
root.geometry("1200x900")

# Khởi tạo camera ngoài hàm capture_camera()
cap = cv2.VideoCapture(2)
# Thêm một biến cap2 để kết nối camera thứ hai
cap2 = cv2.VideoCapture(1)  # Đối số là số thứ tự của camera thứ hai

# StringVar cho các giá trị x, y, m, n, i, và j
x_value = tk.StringVar()
y_value = tk.StringVar()
m_value = tk.StringVar()
n_value = tk.StringVar()
i_value = tk.StringVar()
j_value = tk.StringVar()
text_value = tk.StringVar()
thoigianra_value = tk.StringVar()
thoigian_value = tk.StringVar()

# StringVar cho giá tiền
gia_tien_value = tk.StringVar()
gia_tien_value.set("N/A")


x_value.set("N/A")
y_value.set("N/A")
m_value.set("N/A")
n_value.set("N/A")
i_value.set("N/A")
j_value.set("N/A")
text_value.set("N/A")
thoigianra_value.set("N/A")
thoigian_value.set("N/A")


# Cờ điều khiển vòng lặp
running = True
camera_running = True  # Đây là biến để kiểm soát trạng thái của luồng camera

# Cấu hình kết nối cơ sở dữ liệu
DRIVER_NAME = 'SQL Server'
SERVER_NAME = 'DESKTOP-FTFBRMJ\\SQL2022'
DATABASE_NAME = 'dai'
USERNAME = 'sa'
PASSWORD = 'thaydat12'

# Chuỗi kết nối
connection_string = f"""
    DRIVER={{{DRIVER_NAME}}};
    SERVER={SERVER_NAME};
    DATABASE={DATABASE_NAME};
    UID={USERNAME};
    PWD={PASSWORD};
"""

def save_to_database(text, current_time, current_time1, i_value):

    try:
        conn = odbc.connect(connection_string)
        cursor = conn.cursor()

        select_query = "SELECT ThoiGian, ThoiGianRa FROM BANGTRANGTHAI WHERE TenBienSo = ? AND TenIdThe = ?"
        cursor.execute(select_query, (text, i_value.get()))
        result = cursor.fetchone()

        if result:
            print("Dữ liệu đã tồn tại trong cơ sở dữ liệu.")
            thoigian_value.set(result[0])
            thoigianra_value.set(result[1])

            update_query = "UPDATE BANGTRANGTHAI SET ThoiGianRa = ? WHERE TenBienSo = ? AND TenIdThe = ?"
            cursor.execute(update_query, (current_time1, text, i_value.get()))
            conn.commit()

            DataSerial.write(b'180\r')

            delete_query = "DELETE FROM BANGTRANGTHAI WHERE TenBienSo = ? AND TenIdThe = ?"
            cursor.execute(delete_query, (text, i_value.get()))
            conn.commit()

            update_bangluutru_query = "UPDATE BANGLUUTRU SET ThoiGianRa = ? WHERE TenBienSo = ? AND TenIdThe = ? AND ThoiGianRa IS NULL"
            cursor.execute(update_bangluutru_query, (current_time1, text, i_value.get()))
            conn.commit()

            thoigianra_value.set(current_time1)

            # Tính giá tiền
            gia_tien = tinh_gia_tien(result[0], current_time1)

            # Cập nhật giá tiền lên giao diện người dùng
            cap_nhat_gia_tien(gia_tien)

        else:
            insert_query = "INSERT INTO BANGTRANGTHAI (TenBienSo, NgayVao, ThoiGian, TenIdThe) VALUES (?, ?, ?, ?)"
            cursor.execute(insert_query, (text, current_time, current_time1, i_value.get()))
            conn.commit()
            DataSerial.write(b'90\r')
            print("Dữ liệu đã được lưu vào cơ sở dữ liệu.")

            insert_new_table_query = "INSERT INTO BANGLUUTRU (TenBienSo, NgayVao, ThoiGian, TenIdThe) VALUES (?, ?, ?, ?)"
            cursor.execute(insert_new_table_query, (text, current_time, current_time1, i_value.get()))
            conn.commit()
            print("Dữ liệu đã được lưu vào bảng mới BANGMOI.")

            thoigian_value.set(current_time1)
            thoigianra_value.set("N/A")

    except Exception as e:
        print(f"Lỗi khi lưu vào cơ sở dữ liệu: {e}")

    finally:
        if conn:
            conn.close()

def tinh_gia_tien(thoigian_vao, thoigian_ra):
    try:
        fmt = "%H:%M:%S"

        # Loại bỏ số sau dấu chấm thừa trong chuỗi thời gian
        thoigian_vao = loai_bo_sau_dau_cham_thua(thoigian_vao)
        thoigian_ra = loai_bo_sau_dau_cham_thua(thoigian_ra)

        thoigian_vao = datetime.datetime.strptime(thoigian_vao, fmt)
        thoigian_ra = datetime.datetime.strptime(thoigian_ra, fmt)

        delta_time = thoigian_ra - thoigian_vao
        total_seconds = delta_time.total_seconds()

        if total_seconds < 8 * 3600:
            gia_tien = 40000
        elif total_seconds > 12 * 3600:
            gia_tien = 100000
        else:
            gia_tien = 70000

        return gia_tien

    except ValueError as e:
        print(f"Lỗi khi tính giá tiền: {e}")
        return None

def loai_bo_sau_dau_cham_thua(str_time):
    try:
        parts = str_time.split('.')
        return parts[0]  # Trả về phần trước dấu chấm
    except Exception as e:
        print(f"Lỗi khi loại bỏ phần thừa sau dấu chấm: {e}")
        return str_time

def cap_nhat_gia_tien(gia_tien):
    if gia_tien is not None:
        gia_tien_str = "{:,}".format(gia_tien)
        gia_tien_value.set(gia_tien_str)
        print("Giá tiền:", gia_tien_str)
    else:
        gia_tien_value.set("N/A")
# Function to capture frames from the camera
def capture_camera():
    global cap
    while running:
        ret, frame = cap.read()  # Read a frame from the camera
        if not ret:
            break

        # Convert the OpenCV frame to PIL format
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame = Image.fromarray(frame)

        # Resize the frame if needed
        frame = frame.resize((400, 300), Image.LANCZOS)

        # Update the label with the new frame
        root.after(10, update_label, frame)  # Schedule updating label with the new frame

    # Release the camera
    cap.release()


# Tạo một luồng mới để chạy camera thứ hai
def capture_camera2():
    global cap2
    while running:
        ret, frame = cap2.read()
        if not ret:
            break
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame = Image.fromarray(frame)
        frame = frame.resize((400, 300), Image.LANCZOS)
        root.after(10, update_label2, frame)


# Function to update the label with the new frame
def update_label(frame):
    # Convert the PIL image to Tkinter format
    img = ImageTk.PhotoImage(frame)

    # Update the label with the new frame
    camera_label.img = img
    camera_label.config(image=img)

def update_label2(frame):

    img = ImageTk.PhotoImage(frame)

    camera_label2.img = img
    camera_label2.config(image=img)

# Cập nhật các giá trị x, y, m, n, i, và j
def update_values():
    global running
    while running:
        try:
            if DataSerial.in_waiting > 0:
                data = DataSerial.readline()
                data = data.decode('utf-8').strip()  # Decode byte data to string
                print(data)

                if "ID" in data:
                    id_data = data.split(",")[0].split(":")[1].strip()
                    state_data = data.split(",")[1].split(":")[1].strip()

                    i_value.set(id_data)
                    j_value.set(state_data)


                SpitData = data.split(',')
                print(SpitData)

                if len(SpitData) >= 4:
                    x = str(SpitData[0]).split(":")[1].strip()
                    y = str(SpitData[1]).split(":")[1].strip()
                    m = str(SpitData[2]).split(":")[1].strip()
                    n = str(SpitData[3]).split(":")[1].strip()

                    print('x = ', x)
                    print('y = ', y)
                    print('m = ', m)
                    print('n = ', n)

                    # Cập nhật các giá trị StringVar
                    x_value.set(x)
                    y_value.set(y)
                    m_value.set(m)
                    n_value.set(n)
        except serial.SerialException as e:
            print(f"SerialException: {e}")
            # Có thể thêm xử lý tại đây nếu cần

        time.sleep(0.1)


# Hàm nhận diện văn bản từ hình ảnh và cập nhật giá trị lên giao diện người dùng
def recognize_text_and_update_ui(image_path):
    # Tiến hành nhận diện văn bản và cập nhật giao diện người dùng
    recognized_text = recognize_text(image_path)
    text_value.set(recognized_text)

def recognize_text(image_path):
    # Tải và thay đổi kích thước hình ảnh
    imgHinhGocPIL = Image.open(image_path).resize((500, 300))
    Width, Height = imgHinhGocPIL.size

    # Phát hiện đường viền và xử lý bổ sung
    imgHinhGoc = np.array(imgHinhGocPIL)
    gray = cv2.cvtColor(imgHinhGoc, cv2.COLOR_BGR2GRAY)
    edged = cv2.Canny(gray, 30, 200)
    cnts = cv2.findContours(edged.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    cnts = imutils.grab_contours(cnts)
    cnts = sorted(cnts, key=cv2.contourArea, reverse=True)

    screenCnt = None
    for c in cnts:
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
        if len(approx) == 4:
            screenCnt = approx
            break

    if screenCnt is not None:
        cv2.drawContours(imgHinhGoc, [screenCnt], -1, (0, 255, 0), 2)
        mask = np.zeros(gray.shape, np.uint8)
        new_image = cv2.drawContours(mask, [screenCnt], 0, 255, -1)
        new_image = cv2.bitwise_and(imgHinhGoc, imgHinhGoc, mask=mask)

        (x, y) = np.where(mask == 255)
        (topx, topy) = (np.min(x), np.min(y))
        (bottomx, bottomy) = (np.max(x), np.max(y))
        Cropped = gray[topx:bottomx + 1, topy:bottomy + 1]

        # Chuyển hình ảnh sang văn bản bằng Tesseract OCR
        text = pytesseract.image_to_string(Cropped, lang='eng')

        # Xử lý văn bản nhận dạng được
        lines = text.split('\n')
        combined_text = ''.join(lines)
        print("Recognized Text:", combined_text)

        # Lấy thời gian hiện tại
        current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        current_time1 = time.strftime("%H:%M:%S", time.localtime()).split('.')[0]  # Lấy chỉ phần không có thập phân

        # Lưu kết quả văn bản vào cơ sở dữ liệu
        save_to_database(combined_text, current_time, current_time1, i_value)
        return combined_text
    else:
        print("Không tìm thấy vùng chứa văn bản.")
        return "N/A"



# Tạo thư mục để lưu ảnh
save_dir = 'captured_images'
if not os.path.exists(save_dir):
    os.makedirs(save_dir)

# Danh sách để lưu trữ các ảnh
images = []

# Biến 'cap' được đặt ở mức global để có thể truy cập trong các hàm
cap = cv2.VideoCapture(2)  # Mở camera ở ngoài hàm capture_image


# Hàm chụp ảnh từ camera và nhận diện văn bản
def capture_image_and_recognize():
    ret, frame = cap.read()
    if ret:
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(frame_rgb)
        images.append(image)

        image_path = os.path.join(save_dir, f'captured_image_{len(images)}.jpg')
        image.save(image_path)
        messagebox.showinfo('Thông báo', f'Đã lưu ảnh vào {image_path}')

        # Tiến hành nhận diện văn bản và cập nhật giá trị lên giao diện người dùng
        recognize_text_and_update_ui(image_path)
    else:
        messagebox.showerror('Lỗi', 'Không thể chụp ảnh.')

# Hàm chụp ảnh từ camera và nhận diện văn bản
def capture_image_and_recognize2():
    ret, frame = cap2.read()
    if ret:
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(frame_rgb)
        images.append(image)

        image_path = os.path.join(save_dir, f'captured_image_{len(images)}.jpg')
        image.save(image_path)
        messagebox.showinfo('Thông báo', f'Đã lưu ảnh vào {image_path}')

        # Tiến hành nhận diện văn bản và cập nhật giá trị lên giao diện người dùng
        recognize_text_and_update_ui(image_path)
    else:
        messagebox.showerror('Lỗi', 'Không thể chụp ảnh.')


# Hàm bắt sự kiện chọn hình ảnh
def choose_image():
    image_path = filedialog.askopenfilename()
    if image_path:
        text = recognize_text(image_path)
        text_value.set(text)


# Khởi động luồng cập nhật các giá trị x, y, m, n, i, và j
thread = threading.Thread(target=update_values)
thread.start()

# Create a label to display the camera feed
camera_label = tk.Label(root)
camera_label.grid(column=2, row=1, rowspan=14)

camera_label2 = tk.Label(root)
camera_label2.grid(column=3, row=1, rowspan=14)

# Start capturing frames from the camera in a separate thread
camera_thread = threading.Thread(target=capture_camera)
camera_thread.start()
# Khởi động luồng cho camera thứ hai
camera_thread2 = threading.Thread(target=capture_camera2)
camera_thread2.start()

# Labels để hiển thị các giá trị x, y, m, n, i, và j
labelx = tk.Label(root, text="VỊ TRÍ 1: ", font=("Arial", 10))
labelx.grid(column=1, row=1)

x_label = tk.Label(root, textvariable=x_value, background="blue", foreground="white", font=("Arial", 10))
x_label.grid(column=1, row=2)

labely = tk.Label(root, text="VỊ TRÍ 2: ", font=("Arial", 10))
labely.grid(column=1, row=3)

y_label = tk.Label(root, textvariable=y_value, background="blue", foreground="white", font=("Arial", 10))
y_label.grid(column=1, row=4)

labelm = tk.Label(root, text="VỊ TRÍ 3: ", font=("Arial", 10))
labelm.grid(column=1, row=5)

m_label = tk.Label(root, textvariable=m_value, background="blue", foreground="white", font=("Arial", 10))
m_label.grid(column=1, row=6)

labeln = tk.Label(root, text="VỊ TRÍ 4: ", font=("Arial", 10))
labeln.grid(column=1, row=7)

n_label = tk.Label(root, textvariable=n_value, background="blue", foreground="white", font=("Arial", 10))
n_label.grid(column=1, row=8)

labeli = tk.Label(root, text="ID THẺ XE: ", font=("Arial", 10))
labeli.grid(column=1, row=9)

i_label = tk.Label(root, textvariable=i_value, background="blue", foreground="white", font=("Arial", 10))
i_label.grid(column=1, row=10)

#labelj = tk.Label(root, text="TRẠNG THÁI: ", font=("Arial", 10))
#labelj.grid(column=1, row=11)

#j_label = tk.Label(root, textvariable=j_value, background="blue", foreground="white", font=("Arial", 10))
#j_label.grid(column=1, row=12)

# Button để chọn hình ảnh
#choose_button = tk.Button(root, text="Chọn hình ảnh", command=choose_image)
#choose_button.grid(column=1, row=13)

# Button để chụp ảnh và nhận diện văn bản
capture_button = tk.Button(root, text='Nhận diện biển số xe vào', command=capture_image_and_recognize)
capture_button.grid(column=1, row=14)

# Button để chụp ảnh và nhận diện văn bản
capture_button = tk.Button(root, text='Nhận diện biển số xe ra', command=capture_image_and_recognize2)
capture_button.grid(column=1, row=15)

# Label để hiển thị văn bản nhận dạng được
text_label = tk.Label(root, textvariable=text_value, background="blue", foreground="white", font=("Arial", 10))
text_label.grid(column=1, row=16)

label_thoigianra = Label(root, text="ThoiGianRa:")
label_thoigianra.grid(row=17, column=0, sticky=tk.E)
entry_thoigianra = Label(root, textvariable=thoigianra_value)
entry_thoigianra.grid(row=17, column=1, sticky=tk.W)

label_thoigian = Label(root, text="ThoiGianVao:")
label_thoigian.grid(row=18, column=0, sticky=tk.E)
entry_thoigian = Label(root, textvariable=thoigian_value)
entry_thoigian.grid(row=18, column=1, sticky=tk.W)

# Label để hiển thị giá tiền
label_gia_tien = tk.Label(root, text="Giá Tiền:", font=("Arial", 10))
label_gia_tien.grid(row=19, column=0, sticky=tk.E)

# Label để hiển thị giá tiền được cập nhật từ mã
gia_tien_label = tk.Label(root, textvariable=gia_tien_value, background="blue", foreground="white", font=("Arial", 10))
gia_tien_label.grid(row=19, column=1, sticky=tk.W)



# Hàm thoát ứng dụng
def exit_app():
    global running, camera_running  # Sử dụng biến toàn cục
    running = False
    camera_running = False  # Dừng luồng của camera
    root.quit()


exit_button = tk.Button(root, text="Thoát", command=exit_app)
exit_button.place(x=130, y=640)

# Vòng lặp chính của Tkinter
root.mainloop()
