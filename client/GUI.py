#!/usr/bin/python
# -*- coding: UTF-8 -*-
# File name   : client.py
# Description : client  
# Website	 : www.adeept.com
# E-mail	  : support@adeept.com
# Author	  : William
# Date		: 2018/08/22

from socket import *
import sys
import time
import threading as thread
import tkinter as tk

try:#1
	import cv2
	import zmq
	import base64
	import numpy as np
except:
	print("Couldn't import OpenCV, you need to install it first.")

ip_stu=1		#Shows connection status
c_f_stu = 0
c_b_stu = 0
c_l_stu = 0
c_r_stu = 0
c_ls_stu= 0
c_rs_stu= 0
funcMode= 0
tcpClicSock = ''
root = ''
stat = 0

Switch_3 = 0
Switch_2 = 0
Switch_1 = 0
SmoothMode = 0

########>>>>>VIDEO<<<<<########

def video_thread():
	global footage_socket, font, frame_num, fps
	context = zmq.Context()
	footage_socket = context.socket(zmq.SUB)
	footage_socket.bind('tcp://*:5555')
	footage_socket.setsockopt_string(zmq.SUBSCRIBE, np.unicode(''))

	font = cv2.FONT_HERSHEY_SIMPLEX

	frame_num = 0
	fps = 0

def get_FPS():
	global frame_num, fps
	while 1:
		try:
			time.sleep(1)
			fps = frame_num
			frame_num = 0
		except:
			time.sleep(1)

def opencv_r():
	global frame_num
	while True:
		try:
			frame = footage_socket.recv_string()
			img = base64.b64decode(frame)
			npimg = np.frombuffer(img, dtype=np.uint8)
			source = cv2.imdecode(npimg, 1)
			cv2.putText(source,('PC FPS: %s'%fps),(40,20), font, 0.5,(255,255,255),1,cv2.LINE_AA)
			try:
				cv2.putText(source,('CPU Temperature: %s'%CPU_TEP),(370,350), font, 0.5,(128,255,128),1,cv2.LINE_AA)
				cv2.putText(source,('CPU Usage: %s'%CPU_USE),(370,380), font, 0.5,(128,255,128),1,cv2.LINE_AA)
				cv2.putText(source,('RAM Usage: %s'%RAM_USE),(370,410), font, 0.5,(128,255,128),1,cv2.LINE_AA)

				#cv2.line(source,(320,240),(260,300),(255,255,255),1)
				#cv2.line(source,(210,300),(260,300),(255,255,255),1)

				#cv2.putText(source,('%sm'%ultra_data),(210,290), font, 0.5,(255,255,255),1,cv2.LINE_AA)
			except:
				pass
			#cv2.putText(source,('%sm'%ultra_data),(210,290), font, 0.5,(255,255,255),1,cv2.LINE_AA)
			cv2.imshow("Stream", source)
			frame_num += 1
			cv2.waitKey(1)

		except:
			time.sleep(0.5)
			break

fps_threading=thread.Thread(target=get_FPS)		 #Define a thread for FPV and OpenCV
fps_threading.setDaemon(True)							 #'True' means it is a front thread,it would close when the mainloop() closes
fps_threading.start()									 #Thread starts

video_threading=thread.Thread(target=video_thread)		 #Define a thread for FPV and OpenCV
video_threading.setDaemon(True)							 #'True' means it is a front thread,it would close when the mainloop() closes
video_threading.start()									 #Thread starts

########>>>>>VIDEO<<<<<########


def replace_num(initial,new_num):   #Call this function to replace data in '.txt' file
	newline=""
	str_num=str(new_num)
	with open("./ip.txt","r") as f:
		for line in f.readlines():
			if(line.find(initial) == 0):
				line = initial+"%s" %(str_num)
			newline += line
	with open("./ip.txt","w") as f:
		f.writelines(newline)	#Call this function to replace data in '.txt' file


def num_import(initial):			#Call this function to import data from '.txt' file
	with open("./ip.txt") as f:
		for line in f.readlines():
			if(line.find(initial) == 0):
				r=line
	begin=len(list(initial))
	snum=r[begin:]
	n=snum
	return n	


def call_forward(event):		 #When this function is called,client commands the car to move forward
	global c_f_stu
	if c_f_stu == 0:
		tcpClicSock.send(('forward').encode())
		c_f_stu=1


def call_back(event):			#When this function is called,client commands the car to move backward
	global c_b_stu 
	if c_b_stu == 0:
		tcpClicSock.send(('backward').encode())
		c_b_stu=1


def call_FB_stop(event):			#When this function is called,client commands the car to stop moving
	global c_f_stu,c_b_stu,c_l_stu,c_r_stu,c_ls_stu,c_rs_stu
	c_f_stu=0
	c_b_stu=0
	tcpClicSock.send(('DS').encode())


def call_Turn_stop(event):			#When this function is called,client commands the car to stop moving
	global c_f_stu,c_b_stu,c_l_stu,c_r_stu,c_ls_stu,c_rs_stu
	c_l_stu=0
	c_r_stu=0
	c_ls_stu=0
	c_rs_stu=0
	tcpClicSock.send(('TS').encode())


def call_Left(event):			#When this function is called,client commands the car to turn left
	global c_l_stu
	if c_l_stu == 0:
		tcpClicSock.send(('left').encode())
		c_l_stu=1


def call_Right(event):		   #When this function is called,client commands the car to turn right
	global c_r_stu
	if c_r_stu == 0:
		tcpClicSock.send(('right').encode())
		c_r_stu=1


def call_LeftSide(event):
	global c_ls_stu
	if c_ls_stu == 0:
		tcpClicSock.send(('leftside').encode())
		c_ls_stu=1


def call_RightSide(event):
	global c_rs_stu
	if c_rs_stu == 0:
		tcpClicSock.send(('rightside').encode())
		c_rs_stu=1


def call_headup(event):
	tcpClicSock.send(('headup').encode())


def call_headdown(event):
	tcpClicSock.send(('headdown').encode())


def call_headleft(event):
	tcpClicSock.send(('headleft').encode())


def call_headright(event):
	tcpClicSock.send(('headright').encode())


def call_headhome(event):
	tcpClicSock.send(('headhome').encode())


def call_steady(event):
	if funcMode == 0:
		tcpClicSock.send(('steady').encode())
	else:
		tcpClicSock.send(('funEnd').encode())


def call_FindColor(event):
	if funcMode == 0:
		tcpClicSock.send(('FindColor').encode())
	else:
		tcpClicSock.send(('funEnd').encode())


def call_WatchDog(event):
	if funcMode == 0:
		tcpClicSock.send(('WatchDog').encode())
	else:
		tcpClicSock.send(('funEnd').encode())


def call_Smooth(event):
	if SmoothMode == 0:
		tcpClicSock.send(('Smooth_on').encode())
	else:
		tcpClicSock.send(('Smooth_off').encode())


def call_Switch_1(event):
	if Switch_1 == 0:
		tcpClicSock.send(('Switch_1_on').encode())
	else:
		tcpClicSock.send(('Switch_1_off').encode())


def call_Switch_2(event):
	if Switch_2 == 0:
		tcpClicSock.send(('Switch_2_on').encode())
	else:
		tcpClicSock.send(('Switch_2_off').encode())


def call_Switch_3(event):
	if Switch_3 == 0:
		tcpClicSock.send(('Switch_3_on').encode())
	else:
		tcpClicSock.send(('Switch_3_off').encode())


def all_btn_red():
	Btn_Steady.config(bg='#FF6D00', fg='#000000')
	Btn_FindColor.config(bg='#FF6D00', fg='#000000')
	Btn_WatchDog.config(bg='#FF6D00', fg='#000000')
	Btn_Fun4.config(bg='#FF6D00', fg='#000000')
	Btn_Fun5.config(bg='#FF6D00', fg='#000000')
	Btn_Fun6.config(bg='#FF6D00', fg='#000000')


def all_btn_normal():
	Btn_Steady.config(bg=color_btn, fg=color_text)
	Btn_FindColor.config(bg=color_btn, fg=color_text)
	Btn_WatchDog.config(bg=color_btn, fg=color_text)
	Btn_Fun4.config(bg=color_btn, fg=color_text)
	Btn_Fun5.config(bg=color_btn, fg=color_text)
	Btn_Fun6.config(bg=color_btn, fg=color_text)


def connection_thread():
	global funcMode, Switch_3, Switch_2, Switch_1, SmoothMode
	while 1:
		car_info = (tcpClicSock.recv(BUFSIZ)).decode()
		if not car_info:
			continue

		elif 'FindColor' in car_info:
			funcMode = 1
			all_btn_red()
			Btn_FindColor.config(bg='#00E676')

		elif 'steady' in car_info:
			funcMode = 1
			all_btn_red()
			Btn_Steady.config(bg='#00E676')

		elif 'WatchDog' in car_info:
			funcMode = 1
			all_btn_red()
			Btn_WatchDog.config(bg='#00E676')

		elif 'Smooth_on' in car_info:
			SmoothMode = 1
			Btn_Smooth.config(bg='#4CAF50')

		elif 'Smooth_off' in car_info:
			SmoothMode = 0
			Btn_Smooth.config(bg=color_btn)

		elif 'Switch_3_on' in car_info:
			Switch_3 = 1
			Btn_Switch_3.config(bg='#4CAF50')

		elif 'Switch_2_on' in car_info:
			Switch_2 = 1
			Btn_Switch_2.config(bg='#4CAF50')

		elif 'Switch_1_on' in car_info:
			Switch_1 = 1
			Btn_Switch_1.config(bg='#4CAF50')

		elif 'Switch_3_off' in car_info:
			Switch_3 = 0
			Btn_Switch_3.config(bg=color_btn)

		elif 'Switch_2_off' in car_info:
			Switch_2 = 0
			Btn_Switch_2.config(bg=color_btn)

		elif 'Switch_1_off' in car_info:
			Switch_1 = 0
			Btn_Switch_1.config(bg=color_btn)

		elif 'CVFL_on' in car_info:
			function_stu = 1
			Btn_CVFL.config(bg='#4CAF50')

		elif 'CVFL_off' in car_info:
			function_stu = 0
			Btn_CVFL.config(bg='#212121')

		elif 'FunEnd' in car_info:
			funcMode = 0
			all_btn_normal()

		print(car_info)


def Info_receive():
	global CPU_TEP,CPU_USE,RAM_USE
	HOST = ''
	INFO_PORT = 2256							#Define port serial 
	ADDR = (HOST, INFO_PORT)
	InfoSock = socket(AF_INET, SOCK_STREAM)
	InfoSock.setsockopt(SOL_SOCKET,SO_REUSEADDR,1)
	InfoSock.bind(ADDR)
	InfoSock.listen(5)					  #Start server,waiting for client
	InfoSock, addr = InfoSock.accept()
	print('Info connected')
	while 1:
		try:
			info_data = ''
			info_data = str(InfoSock.recv(BUFSIZ).decode())
			info_get = info_data.split()
			CPU_TEP,CPU_USE,RAM_USE= info_get
			#print('cpu_tem:%s\ncpu_use:%s\nram_use:%s'%(CPU_TEP,CPU_USE,RAM_USE))
			CPU_TEP_lab.config(text='CPU Temp: %s℃'%CPU_TEP)
			CPU_USE_lab.config(text='CPU Usage: %s'%CPU_USE)
			RAM_lab.config(text='RAM Usage: %s'%RAM_USE)
		except:
			pass


def socket_connect():	 #Call this function to connect with the server
	global ADDR,tcpClicSock,BUFSIZ,ip_stu,ipaddr
	ip_adr=E1.get()	   #Get the IP address from Entry

	if ip_adr == '':	  #If no input IP address in Entry,import a default IP
		ip_adr=num_import('IP:')
		l_ip_4.config(text='Connecting')
		l_ip_4.config(bg='#FF8F00')
		l_ip_5.config(text='Default:%s'%ip_adr)
		pass
	
	SERVER_IP = ip_adr
	SERVER_PORT = 10223   #Define port serial 
	BUFSIZ = 1024		 #Define buffer size
	ADDR = (SERVER_IP, SERVER_PORT)
	tcpClicSock = socket(AF_INET, SOCK_STREAM) #Set connection value for socket

	for i in range (1,6): #Try 5 times if disconnected
		#try:
		if ip_stu == 1:
			print("Connecting to server @ %s:%d..." %(SERVER_IP, SERVER_PORT))
			print("Connecting")
			tcpClicSock.connect(ADDR)		#Connection with the server
		
			print("Connected")
		
			l_ip_5.config(text='IP:%s'%ip_adr)
			l_ip_4.config(text='Connected')
			l_ip_4.config(bg='#558B2F')

			replace_num('IP:',ip_adr)
			E1.config(state='disabled')	  #Disable the Entry
			Btn14.config(state='disabled')   #Disable the Entry
			
			ip_stu=0						 #'0' means connected

			connection_threading=thread.Thread(target=connection_thread)		 #Define a thread for FPV and OpenCV
			connection_threading.setDaemon(True)							 #'True' means it is a front thread,it would close when the mainloop() closes
			connection_threading.start()									 #Thread starts

			info_threading=thread.Thread(target=Info_receive)		 #Define a thread for FPV and OpenCV
			info_threading.setDaemon(True)							 #'True' means it is a front thread,it would close when the mainloop() closes
			info_threading.start()									 #Thread starts

			video_threading=thread.Thread(target=opencv_r)		 #Define a thread for FPV and OpenCV
			video_threading.setDaemon(True)							 #'True' means it is a front thread,it would close when the mainloop() closes
			video_threading.start()									 #Thread starts

			break
		else:
			print("Cannot connecting to server,try it latter!")
			l_ip_4.config(text='Try %d/5 time(s)'%i)
			l_ip_4.config(bg='#EF6C00')
			print('Try %d/5 time(s)'%i)
			ip_stu=1
			time.sleep(1)
			continue

	if ip_stu == 1:
		l_ip_4.config(text='Disconnected')
		l_ip_4.config(bg='#F44336')


def connect(event):	   #Call this function to connect with the server
	if ip_stu == 1:
		sc=thread.Thread(target=socket_connect) #Define a thread for connection
		sc.setDaemon(True)					  #'True' means it is a front thread,it would close when the mainloop() closes
		sc.start()							  #Thread starts


def connect_click():	   #Call this function to connect with the server
	if ip_stu == 1:
		sc=thread.Thread(target=socket_connect) #Define a thread for connection
		sc.setDaemon(True)					  #'True' means it is a front thread,it would close when the mainloop() closes
		sc.start()							  #Thread starts


def set_R(event):
	time.sleep(0.03)
	tcpClicSock.send(('wsR %s'%var_R.get()).encode())


def set_G(event):
	time.sleep(0.03)
	tcpClicSock.send(('wsG %s'%var_G.get()).encode())


def set_B(event):
	time.sleep(0.03)
	tcpClicSock.send(('wsB %s'%var_B.get()).encode())


def EC_send(event):#z
		tcpClicSock.send(('setEC %s'%var_ec.get()).encode())
		time.sleep(0.03)


def EC_default(event):#z
	var_ec.set(0)
	tcpClicSock.send(('defEC').encode())


def scale_FL(x,y,w):#1
	global Btn_CVFL
	def lip1_send(event):
		time.sleep(0.03)
		tcpClicSock.send(('lip1 %s'%var_lip1.get()).encode())

	def lip2_send(event):
		time.sleep(0.03)
		tcpClicSock.send(('lip2 %s'%var_lip2.get()).encode())

	def err_send(event):
		time.sleep(0.03)
		tcpClicSock.send(('err %s'%var_err.get()).encode())

	def call_Render(event):
		tcpClicSock.send(('Render').encode())

	def call_CVFL(event):
		tcpClicSock.send(('CVFL').encode())

	def call_WB(event):
		tcpClicSock.send(('WBswitch').encode())

	Scale_lip1 = tk.Scale(root,label=None,
	from_=0,to=480,orient=tk.HORIZONTAL,length=w,
	showvalue=1,tickinterval=None,resolution=1,variable=var_lip1,troughcolor='#212121',command=lip1_send,fg=color_text,bg=color_bg,highlightthickness=0)
	Scale_lip1.place(x=x,y=y)							#Define a Scale and put it in position

	Scale_lip2 = tk.Scale(root,label=None,
	from_=0,to=480,orient=tk.HORIZONTAL,length=w,
	showvalue=1,tickinterval=None,resolution=1,variable=var_lip2,troughcolor='#212121',command=lip2_send,fg=color_text,bg=color_bg,highlightthickness=0)
	Scale_lip2.place(x=x,y=y+30)						#Define a Scale and put it in position

	Scale_err = tk.Scale(root,label=None,
	from_=0,to=200,orient=tk.HORIZONTAL,length=w,
	showvalue=1,tickinterval=None,resolution=1,variable=var_err,troughcolor='#212121',command=err_send,fg=color_text,bg=color_bg,highlightthickness=0)
	Scale_err.place(x=x,y=y+60)							#Define a Scale and put it in position

	canvas_cover=tk.Canvas(root,bg=color_bg,height=30,width=510,highlightthickness=0)
	canvas_cover.place(x=x,y=y+90)

	Btn_Render = tk.Button(root, width=10, text='Render',fg=color_text,bg='#212121',relief='ridge')
	Btn_Render.place(x=x+w+111,y=y+20)
	Btn_Render.bind('<ButtonPress-1>', call_Render)

	Btn_CVFL = tk.Button(root, width=10, text='CV FL',fg=color_text,bg='#212121',relief='ridge')
	Btn_CVFL.place(x=x+w+21,y=y+20)
	Btn_CVFL.bind('<ButtonPress-1>', call_CVFL)

	Btn_WB = tk.Button(root, width=23, text='LineColorSwitch',fg=color_text,bg='#212121',relief='ridge')
	Btn_WB.place(x=x+w+21,y=y+60)
	Btn_WB.bind('<ButtonPress-1>', call_WB)


def loop():					  #GUI
	global tcpClicSock,root,E1,connect,l_ip_4,l_ip_5,color_btn,color_text,Btn14,CPU_TEP_lab,CPU_USE_lab,RAM_lab,canvas_ultra,color_text,var_lip1,var_lip2,var_err,var_R,var_B,var_G,var_ec,Btn_Steady,Btn_FindColor,Btn_WatchDog,Btn_Fun4,Btn_Fun5,Btn_Fun6,Btn_Switch_1,Btn_Switch_2,Btn_Switch_3,Btn_Smooth,color_bg   #1 The value of tcpClicSock changes in the function loop(),would also changes in global so the other functions could use it.
	while True:
		color_bg='#000000'		#Set background color
		color_text='#E1F5FE'	  #Set text color
		color_btn='#0277BD'	   #Set button color
		color_line='#01579B'	  #Set line color
		color_can='#212121'	   #Set canvas color
		color_oval='#2196F3'	  #Set oval color
		target_color='#FF6D00'

		root = tk.Tk()			#Define a window named root
		root.title('Adeept RaspClaws')	  #Main window title
		root.geometry('565x680')  #1 Main window size, middle of the English letter x.
		root.config(bg=color_bg)  #Set the background color of root window

		try:
			logo =tk.PhotoImage(file = 'logo.png')		 #Define the picture of logo,but only supports '.png' and '.gif'
			l_logo=tk.Label(root,image = logo,bg=color_bg) #Set a label to show the logo picture
			l_logo.place(x=30,y=13)						#Place the Label in a right position
		except:
			pass

		CPU_TEP_lab=tk.Label(root,width=18,text='CPU Temp:',fg=color_text,bg='#212121')
		CPU_TEP_lab.place(x=400,y=15)						 #Define a Label and put it in position

		CPU_USE_lab=tk.Label(root,width=18,text='CPU Usage:',fg=color_text,bg='#212121')
		CPU_USE_lab.place(x=400,y=45)						 #Define a Label and put it in position

		RAM_lab=tk.Label(root,width=18,text='RAM Usage:',fg=color_text,bg='#212121')
		RAM_lab.place(x=400,y=75)						 #Define a Label and put it in position

		l_ip=tk.Label(root,width=18,text='Status',fg=color_text,bg=color_btn)
		l_ip.place(x=30,y=110)						   #Define a Label and put it in position

		l_ip_4=tk.Label(root,width=18,text='Disconnected',fg=color_text,bg='#F44336')
		l_ip_4.place(x=400,y=110)						 #Define a Label and put it in position

		l_ip_5=tk.Label(root,width=18,text='Use default IP',fg=color_text,bg=color_btn)
		l_ip_5.place(x=400,y=145)						 #Define a Label and put it in position

		E1 = tk.Entry(root,show=None,width=16,bg="#37474F",fg='#eceff1')
		E1.place(x=180,y=40)							 #Define a Entry and put it in position

		l_ip_3=tk.Label(root,width=10,text='IP Address:',fg=color_text,bg='#000000')
		l_ip_3.place(x=175,y=15)						 #Define a Label and put it in position

		label_openCV=tk.Label(root,width=28,text='OpenCV Status',fg=color_text,bg=color_btn)
		label_openCV.place(x=180,y=110)						 #Define a Label and put it in position

		################################
		#canvas_rec=canvas_ultra.create_rectangle(0,0,340,30,fill = '#FFFFFF',width=0)
		#canvas_text=canvas_ultra.create_text((90,11),text='Ultrasonic Output: 0.75m',fill=color_text)
		################################
		Btn_Smooth = tk.Button(root, width=8, text='Smooth',fg=color_text,bg=color_btn,relief='ridge')
		Btn_Smooth.place(x=240,y=230)
		Btn_Smooth.bind('<ButtonPress-1>', call_Smooth)
		root.bind('<KeyPress-f>', call_Smooth)

		Btn_Switch_1 = tk.Button(root, width=8, text='Port 1',fg=color_text,bg=color_btn,relief='ridge')
		Btn_Switch_2 = tk.Button(root, width=8, text='Port 2',fg=color_text,bg=color_btn,relief='ridge')
		Btn_Switch_3 = tk.Button(root, width=8, text='Port 3',fg=color_text,bg=color_btn,relief='ridge')

		Btn_Switch_1.place(x=30,y=265)
		Btn_Switch_2.place(x=100,y=265)
		Btn_Switch_3.place(x=170,y=265)

		Btn_Switch_1.bind('<ButtonPress-1>', call_Switch_1)
		Btn_Switch_2.bind('<ButtonPress-1>', call_Switch_2)
		Btn_Switch_3.bind('<ButtonPress-1>', call_Switch_3)

		Btn0 = tk.Button(root, width=8, text='Forward',fg=color_text,bg=color_btn,relief='ridge')
		Btn1 = tk.Button(root, width=8, text='Backward',fg=color_text,bg=color_btn,relief='ridge')
		Btn2 = tk.Button(root, width=8, text='Left',fg=color_text,bg=color_btn,relief='ridge')
		Btn3 = tk.Button(root, width=8, text='Right',fg=color_text,bg=color_btn,relief='ridge')

		Btn_LeftSide = tk.Button(root, width=8, text='<--',fg=color_text,bg=color_btn,relief='ridge')
		Btn_LeftSide.place(x=30,y=195)
		Btn_LeftSide.bind('<ButtonPress-1>', call_LeftSide)
		Btn_LeftSide.bind('<ButtonRelease-1>', call_Turn_stop)

		Btn_RightSide = tk.Button(root, width=8, text='-->',fg=color_text,bg=color_btn,relief='ridge')
		Btn_RightSide.place(x=170,y=195)
		Btn_RightSide.bind('<ButtonPress-1>', call_RightSide)
		Btn_RightSide.bind('<ButtonRelease-1>', call_Turn_stop)

		Btn0.place(x=100,y=195)
		Btn1.place(x=100,y=230)
		Btn2.place(x=30,y=230)
		Btn3.place(x=170,y=230)

		Btn0.bind('<ButtonPress-1>', call_forward)
		Btn1.bind('<ButtonPress-1>', call_back)
		Btn2.bind('<ButtonPress-1>', call_Left)
		Btn3.bind('<ButtonPress-1>', call_Right)

		Btn0.bind('<ButtonRelease-1>', call_FB_stop)
		Btn1.bind('<ButtonRelease-1>', call_FB_stop)
		Btn2.bind('<ButtonRelease-1>', call_Turn_stop)
		Btn3.bind('<ButtonRelease-1>', call_Turn_stop)

		root.bind('<KeyPress-w>', call_forward) 
		root.bind('<KeyPress-a>', call_Left)
		root.bind('<KeyPress-d>', call_Right)
		root.bind('<KeyPress-s>', call_back)

		root.bind('<KeyPress-q>', call_LeftSide)
		root.bind('<KeyPress-e>', call_RightSide)
		root.bind('<KeyRelease-q>', call_Turn_stop)
		root.bind('<KeyRelease-e>', call_Turn_stop)

		root.bind('<KeyRelease-w>', call_FB_stop)
		root.bind('<KeyRelease-a>', call_Turn_stop)
		root.bind('<KeyRelease-d>', call_Turn_stop)
		root.bind('<KeyRelease-s>', call_FB_stop)

		Btn_up = tk.Button(root, width=8, text='Up',fg=color_text,bg=color_btn,relief='ridge')
		Btn_down = tk.Button(root, width=8, text='Down',fg=color_text,bg=color_btn,relief='ridge')
		Btn_left = tk.Button(root, width=8, text='Left',fg=color_text,bg=color_btn,relief='ridge')
		Btn_right = tk.Button(root, width=8, text='Right',fg=color_text,bg=color_btn,relief='ridge')
		Btn_home = tk.Button(root, width=8, text='Home',fg=color_text,bg=color_btn,relief='ridge')
		Btn_up.place(x=400,y=195)
		Btn_down.place(x=400,y=265)
		Btn_left.place(x=330,y=230)
		Btn_right.place(x=470,y=230)
		Btn_home.place(x=400,y=230)
		root.bind('<KeyPress-i>', call_headup) 
		root.bind('<KeyPress-k>', call_headdown)
		root.bind('<KeyPress-j>', call_headleft)
		root.bind('<KeyPress-l>', call_headright)
		root.bind('<KeyPress-h>', call_headhome)
		Btn_up.bind('<ButtonPress-1>', call_headup)
		Btn_down.bind('<ButtonPress-1>', call_headdown)
		Btn_left.bind('<ButtonPress-1>', call_headleft)
		Btn_right.bind('<ButtonPress-1>', call_headright)
		Btn_home.bind('<ButtonPress-1>', call_headhome)

		Btn14= tk.Button(root, width=8,height=2, text='Connect',fg=color_text,bg=color_btn,command=connect_click,relief='ridge')
		Btn14.place(x=315,y=15)						  #Define a Button and put it in position

		root.bind('<Return>', connect)

		var_lip1 = tk.StringVar()#1
		var_lip1.set(440)
		var_lip2 = tk.StringVar()
		var_lip2.set(380)
		var_err = tk.StringVar()
		var_err.set(20)

		var_R = tk.StringVar()
		var_R.set(0)

		Scale_R = tk.Scale(root,label=None,
		from_=0,to=255,orient=tk.HORIZONTAL,length=505,
		showvalue=1,tickinterval=None,resolution=1,variable=var_R,troughcolor='#F44336',command=set_R,fg=color_text,bg=color_bg,highlightthickness=0)
		Scale_R.place(x=30,y=330)							#Define a Scale and put it in position

		var_G = tk.StringVar()
		var_G.set(0)

		Scale_G = tk.Scale(root,label=None,
		from_=0,to=255,orient=tk.HORIZONTAL,length=505,
		showvalue=1,tickinterval=None,resolution=1,variable=var_G,troughcolor='#00E676',command=set_G,fg=color_text,bg=color_bg,highlightthickness=0)
		Scale_G.place(x=30,y=360)							#Define a Scale and put it in position

		var_B = tk.StringVar()
		var_B.set(0)

		Scale_B = tk.Scale(root,label=None,
		from_=0,to=255,orient=tk.HORIZONTAL,length=505,
		showvalue=1,tickinterval=None,resolution=1,variable=var_B,troughcolor='#448AFF',command=set_B,fg=color_text,bg=color_bg,highlightthickness=0)
		Scale_B.place(x=30,y=390)							#Define a Scale and put it in position

		var_ec = tk.StringVar() #Z start
		var_ec.set(0)			

		Scale_ExpCom = tk.Scale(root,label='Exposure Compensation Level',
		from_=-25,to=25,orient=tk.HORIZONTAL,length=315,
		showvalue=1,tickinterval=None,resolution=1,variable=var_ec,troughcolor='#212121',command=EC_send,fg=color_text,bg=color_bg,highlightthickness=0)
		Scale_ExpCom.place(x=30,y=610)							#Define a Scale and put it in position

		canvas_cover_exp=tk.Canvas(root,bg=color_bg,height=30,width=510,highlightthickness=0)
		canvas_cover_exp.place(x=30,y=610+50)

		Btn_dEC = tk.Button(root, width=23,height=2, text='Set Default Exposure\nCompensation Level',fg=color_text,bg='#212121',relief='ridge')
		Btn_dEC.place(x=30+315+21,y=610+3)
		Btn_dEC.bind('<ButtonPress-1>', EC_default)	#Z end

		canvas_cover=tk.Canvas(root,bg=color_bg,height=30,width=510,highlightthickness=0)
		canvas_cover.place(x=30,y=420)

		Btn_Steady = tk.Button(root, width=10, text='Steady',fg=color_text,bg=color_btn,relief='ridge')
		Btn_Steady.place(x=30,y=445)
		root.bind('<KeyPress-z>', call_steady)
		Btn_Steady.bind('<ButtonPress-1>', call_steady)

		Btn_FindColor = tk.Button(root, width=10, text='FindColor',fg=color_text,bg=color_btn,relief='ridge')
		Btn_FindColor.place(x=115,y=445)
		root.bind('<KeyPress-z>', call_FindColor)
		Btn_FindColor.bind('<ButtonPress-1>', call_FindColor)

		Btn_WatchDog = tk.Button(root, width=10, text='WatchDog',fg=color_text,bg=color_btn,relief='ridge')
		Btn_WatchDog.place(x=200,y=445)
		root.bind('<KeyPress-z>', call_WatchDog)
		Btn_WatchDog.bind('<ButtonPress-1>', call_WatchDog)

		Btn_Fun4 = tk.Button(root, width=10, text='Function 4',fg=color_text,bg=color_btn,relief='ridge')
		Btn_Fun4.place(x=285,y=445)
		root.bind('<KeyPress-z>', call_WatchDog)
		Btn_Fun4.bind('<ButtonPress-1>', call_WatchDog)

		Btn_Fun5 = tk.Button(root, width=10, text='Function 5',fg=color_text,bg=color_btn,relief='ridge')
		Btn_Fun5.place(x=370,y=445)
		root.bind('<KeyPress-z>', call_WatchDog)
		Btn_Fun5.bind('<ButtonPress-1>', call_WatchDog)

		Btn_Fun6 = tk.Button(root, width=10, text='Function 6',fg=color_text,bg=color_btn,relief='ridge')
		Btn_Fun6.place(x=455,y=445)
		root.bind('<KeyPress-z>', call_WatchDog)
		Btn_Fun6.bind('<ButtonPress-1>', call_WatchDog)

		scale_FL(30,490,315)#1

		global stat
		if stat==0:			  # Ensure the mainloop runs only once
			root.mainloop()  # Run the mainloop()
			stat=1		   # Change the value to '1' so the mainloop() would not run again.


if __name__ == '__main__':
	try:
		loop()				   # Load GUI
	except:
		tcpClicSock.close()		  # Close socket or it may not connect with the server again
		footage_socket.close()
		cv2.destroyAllWindows()
		pass