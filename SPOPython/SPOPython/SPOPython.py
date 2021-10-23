
import serial,time,os
import numpy as np
import matplotlib.pyplot as plt

plt.style.use('ggplot')

ser = serial.Serial('COM3',
                    baudrate=115200)
    
start_word = False

heart_rate_span = [10,250] # max span of heart rate
pts = 1800 # points used for peak finding (400 Hz, I recommend at least 4s (1600 pts)
smoothing_size = 20 # convolution smoothing size

# setup live plotting
plt.ion()
fig = plt.figure(figsize=(14,8))
ax1 = fig.add_subplot(111)
line1, = ax1.plot(np.arange(0,pts),np.zeros((pts,)),linewidth=4,label='Smoothed Data')
line2, = ax1.plot(0,0,label='Gradient Peaks',marker='o',linestyle='',color='k',markersize=10)
ax1.set_xlabel('Time [s]',fontsize=16)
ax1.set_ylabel('Amplitude',fontsize=16)
ax1.legend(fontsize=16)
ax1.tick_params(axis='both',which='major',labelsize=16)
plt.show()

while True:
    t_vec,y_vals = [],[]
    ser.flushInput()  
    try:
        print('Place Finger on Sensor...')
        while len(y_vals)<pts:
            curr_line = ser.readline()
            if start_word == False:
                if curr_line[0:-2]==b'MAX30102':
                    start_word = True
                    print("Program Start")
                    continue
                else:
                    continue
            curr_data = (curr_line[0:-2]).decode("utf-8").split(',')
            if len(curr_data)==3:
                try:
                    t_vec.append(float(curr_data[0])/1000.0)
                    y_vals.append(float(curr_data[2]))
                except:
                    continue
        ser.flushInput() # flush serial port to avoid overflow
        
        # calculating heart rate
        t1 = time.time()
        samp_rate = 1/np.mean(np.diff(t_vec)) # average sample rate for determining peaks
        min_time_bw_samps = (60.0/heart_rate_span[1])
        
        # convolve, calculate gradient, and remove bad endpoints
        y_vals = np.convolve(y_vals,np.ones((smoothing_size,)),'same')/smoothing_size
        red_grad = np.gradient(y_vals,t_vec)
        red_grad[0:int(smoothing_size/2)+1] = np.zeros((int(smoothing_size/2)+1,))
        red_grad[-int(smoothing_size/2)-1:] = np.zeros((int(smoothing_size/2)+1,))  

        y_vals = np.append(np.repeat(y_vals[int(smoothing_size/2)],int(smoothing_size/2)),y_vals[int(smoothing_size/2):-int(smoothing_size/2)])
        y_vals = np.append(y_vals,np.repeat(y_vals[-int(smoothing_size/2)],int(smoothing_size/2)))

        # update plot with new Time and red/IR data
        line1.set_xdata(t_vec)
        line1.set_ydata(y_vals)
        
        ax1.set_xlim([np.min(t_vec),np.max(t_vec)])
        if line1.axes.get_ylim()[0]<0.95*np.min(y_vals) or\
           np.max(y_vals)>line1.axes.get_ylim()[1] or\
           np.min(y_vals)<line1.axes.get_ylim()[0]:
                        ax1.set_ylim([np.min(y_vals),np.max(y_vals)])
        plt.pause(0.001)

        # peak locator algorithm
        peak_locs = np.where(red_grad<-np.std(red_grad))
        if len(peak_locs[0])==0:
            continue
        
        prev_pk = peak_locs[0][0]
        true_peak_locs,pk_loc_span = [],[]
        for ii in peak_locs[0]:
            y_pk = y_vals[ii]
            if (t_vec[ii]-t_vec[prev_pk])<min_time_bw_samps:
                pk_loc_span.append(ii)
            else:
                if pk_loc_span==[]:
                    true_peak_locs.append(ii)
                else:
                    true_peak_locs.append(int(np.mean(pk_loc_span)))
                    pk_loc_span = []

            prev_pk = int(ii)

        t_peaks = [t_vec[kk] for kk in true_peak_locs]
        if t_peaks==[]:
            continue
        else:
            print('BPM: {0:2.1f}'.format(60.0/np.mean(np.diff(t_peaks))))
            ax1.set_title('{0:2.0f} BPM'.format(60.0/np.mean(np.diff(t_peaks))),fontsize=24)
        # plot gradient peaks on original plot to view how BPM is calculated
        scatter_x,scatter_y = [],[]
        for jj in true_peak_locs:
            scatter_x.append(t_vec[jj])
            scatter_y.append(y_vals[jj])
            
        line2.set_data(scatter_x,scatter_y)

        plt.pause(0.001)

        savefig = input("Save Figure? ")
        if savefig=='y':
            plt.savefig('gradient_plot.png',dpi=300,facecolor=[252/255,252/255,252/255])
        elif savefig=='no':
            break
    except KeyboardInterrupt:
        break