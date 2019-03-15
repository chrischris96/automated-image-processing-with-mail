# troubleshooting while reproducing the code: PermissionError:
# https://stackoverflow.com/questions/36434764/permissionerror-errno-13-permission-denied

import email
import getpass
import imaplib
import os
import glob
import errno
import cv2
import numpy as np
import matplotlib.pyplot as plt
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

# create folder where attachments are stored in
detach_dir = '.'
if 'attachments' not in os.listdir(detach_dir):
    os.mkdir('attachments')

# connecting to the IMAP-Server
userName = input('Enter your GMail username: ')
passwd = getpass.getpass('Enter your password: ')

# try:

imapSession = imaplib.IMAP4_SSL('imap.gmail.com', 993)
typ, accountDetails = imapSession.login(userName, passwd)
if typ != 'OK':
    raise print('Not able to sign in!')

# select a mailbox
imapSession.select('INBOX')
# search in mailbox
typ, data = imapSession.search(None, 'ALL')
if typ != 'OK':
    raise print('Error searching Inbox.')

# Iterating over all emails
for msgId in data[0].split():
    typ, messageParts = imapSession.fetch(msgId, '(RFC822)')
    result, data = imapSession.uid('fetch', msgId, '(RFC822)')
    if typ != 'OK':
        print('Error fetching mail.')

    emailBody = messageParts[0][1]

    for response_part in data:
        if isinstance(response_part, tuple):
            msg = email.message_from_string(response_part[1])
            msgFrom = msg['from']
            print(msgFrom)

    # downloading just images
    mail = email.message_from_bytes(emailBody)
    for part in mail.walk():
        if part.get_content_maintype() == 'multipart':
            # print part.as_string()
            continue
        if part.get('Content-Disposition') is None:
            # print part.as_string()
            continue
        fileName = part.get_filename()

        extensions = {".jpg", ".png", ".jpeg"}
        if bool(fileName):  # and (".jpg" or ".jpeg" or ".png" in fileName):
            filePath = os.path.join(detach_dir, 'attachments', fileName)
        if not os.path.isfile(filePath):
            print(fileName)
            fp = open(filePath, 'wb')
            fp.write(part.get_payload(decode=True))
            fp.close()
imapSession.close()
imapSession.logout()

# except:
#     print('Not able to download all attachments.')

# after downloading the data we use them in image analysis
# therefor the path of the images is obtained and saved in a list
# only jpg and jpeg can be used
path_jpeg = '../attachments/*.jpeg'
path_jpg = '../attachments/*.jpg'

files_jpeg = glob.glob(path_jpeg)
files_jpg = glob.glob(path_jpg)
files = files_jpeg + files_jpg

print(files)
# create folder where processed images are stored in
detach_dir = '.'
if 'line_images' not in os.listdir(detach_dir):
    os.mkdir('line_images')

# image analysis takes place here:
for name in files:

    img = cv2.imread(name, cv2.IMREAD_COLOR)

    blurred = cv2.GaussianBlur(img, (3, 3), 0)
    # convert the color image into grayscale
    imgray = cv2.cvtColor(blurred, cv2.COLOR_BGR2GRAY)

    # set a threshold
    # ret, thresh = cv2.threshold(imgray, 90, 255, cv2.THRESH_BINARY)
    ret, thresh = cv2.threshold(imgray, 90, 255, cv2.THRESH_TOZERO)

    # apply Canny detector to detect edges
    low_threshold = 50
    high_threshold = 150
    edges = cv2.Canny(imgray, low_threshold, high_threshold)

    # use HoughLinesP to get the lines
    rho = 1  # distance resolution in pixels of the Hough grid
    theta = np.pi / 180  # angular resolution in radians of the Hough grid
    threshold = 15  # minimum number of votes (intersections in Hough grid cell)
    min_line_length = 50  # minimum number of pixels making up a line
    max_line_gap = 20  # maximum gap in pixels between connectable line segments
    line_image = np.copy(img) * 0  # creating a blank to draw lines on

    lines = cv2.HoughLinesP(edges, rho, theta, threshold, np.array([]),
                            min_line_length, max_line_gap)

    # lines_edges = cv2.addWeighted(img, 0.8, line_image, 1, 0)

    # devide image in four areas where corners of the paper are most likely
    x_thres_min = round(0.35 * len(img))
    x_thres_max = round(0.65 * len(img))

    y_thres_min = round(0.35 * len(img[0]))
    y_thres_max = round(0.65 * len(img[0]))

    for line in lines:
        for x1, y1, x2, y2 in line:
            cv2.line(line_image, (x1, y1), (x2, y2), (255, 255, 255), 5)
    # you can uncomment it to see what it looks like, but the program will break
    # display image
    # cv2.namedWindow('lines', cv2.WINDOW_NORMAL)
    # cv2.imshow('lines', line_image)
    plt.imsave('line_image.png', line_image)

    # Line detection ends

    # path for saving the analysed images is introduced
    path = '../line_images'

    # saving analysed images in a new folder
    cv2.imwrite(os.path.join(path, 'line.jpg'), line_image)
    cv2.waitKey(0)


sample_img = cv2.imread(r"..\line_muster.jpg")
feat_image = cv2.imread(r"..\line_images\line.jpg")

# ORB Detector
orb = cv2.ORB_create()
kp1, des1 = orb.detectAndCompute(sample_img, None)
kp2, des2 = orb.detectAndCompute(feat_image, None)

# Brute Force Matching
bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
matches = bf.match(des1, des2)
matches = sorted(matches, key=lambda x: x.distance)
# checking for the distance
matches_float = []
for m in matches:
    matches_float.append(m.distance)
avr = sum(matches_float)/float(len(matches_float))
matching_result = cv2.drawMatches(sample_img, kp1, feat_image, kp2, matches[:20], None, flags=2)

# imS1 = cv2.resize(sample_img, (960, 540))
# imS2 = cv2.resize(feat_image, (960, 540))
# imS_mr = cv2.resize(matching_result, (960, 540))
#
# cv2.imshow("Img1", imS1)
# cv2.imshow("Img2", imS2)
# cv2.imshow("Matching result", imS_mr)
cv2.waitKey(0)
cv2.destroyAllWindows()

# Create the container email message.
if avr < 18:
    email_user = 'test@gmail.com'
    email_password = 'some_password'
    email_send = 'some_sender@gmail.com'
    subject = 'New foot pattern incoming'

    msg = MIMEMultipart()
    msg['From'] = email_user
    msg['To'] = email_send
    msg['Subject'] = subject

    body = 'Hi, There is a new order for a shoe!' \
           '' \
           '' \
           'Best regards,' \
           'Python'
    msg.attach(MIMEText(body, 'plain'))

    fn = '../line_images/line.jpg'
    attachment = open(fn, 'rb')

    part = MIMEBase('application', 'octet-stream')
    part.set_payload(attachment.read())
    encoders.encode_base64(part)
    part.add_header('Content-Disposition', "attachment; filename= " + fn)

    msg.attach(part)
    text = msg.as_string()
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(email_user, email_password)

    server.sendmail(email_user, email_send, text)
    server.quit()
else:
    email_user = 'test@gmail.com'
    email_password = 'some_password'
    email_send = msgFrom
    subject = 'The drawing was not sufficient'

    msg = MIMEMultipart()
    msg['From'] = email_user
    msg['To'] = email_send
    msg['Subject'] = subject

    body = 'Dear costumer,' \
           '' \
           'The drawing you sent us is just too bad. Please redraw your foot and send the photo to us again.' \
           '' \
           'Best regards,' \
           'Python'
    msg.attach(MIMEText(body, 'plain'))

    fn = '../line_images/line.jpg'
    attachment = open(fn, 'rb')

    part = MIMEBase('application', 'octet-stream')
    part.set_payload(attachment.read())
    encoders.encode_base64(part)
    part.add_header('Content-Disposition', "attachment; filename= " + fn)

    msg.attach(part)
    text = msg.as_string()
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(email_user, email_password)

    server.sendmail(email_user, email_send, text)
    server.quit()