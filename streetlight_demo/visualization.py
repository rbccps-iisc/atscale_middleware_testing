import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Wedge
from matplotlib.collections import PatchCollection
from matplotlib.animation import FuncAnimation
from matplotlib import cm
from matplotlib.lines import Line2D
import time




class PlotStreetlights(object):
    
    def __init__(self, plot_name, N):
        """
        Initialize the plot and populate it with 
        N streetlight poles.
        """
        self.N = N
        self.fig=None   # handles for fig and axis
        self.ax =None   
        self.lights=[]  # handles to circle plots for each light
        self.objects=[] # handles to circle plots representing objects
        self.faults=[]  # handles to circle plots representing faults
        
        
        # generate a canvas
        fig, ax = plt.subplots(figsize=(6,6))
        ax.set(xlim=(0,1),ylim=(0,1))

        # Name the plot
        ax.set_title(plot_name)
        
        plt.ion() # enable plot to be updated dynamically      
        
        # Coordinates of the lights and objects
        x = np.linspace(0.1,0.9,N) # x coordinates
        y_base = 0.2
        y_top  = y_base + 1.0/(N+1)
        y_fault = y_top + 0.1
        
        # y-coordinate to plot activity
        # detected by the streetlight
        y_object = 0.15
        
        # draw horizontal lines representing the street
        ax.add_line(Line2D([0,1], [y_base,y_base], color="sienna",linewidth=2,zorder=1))
        ax.add_line(Line2D([0,1], [y_base/2,y_base/2], color="yellow",linewidth=2,zorder=1,linestyle="--"))
        
        # draw lines representing the light poles.
        for i in range(N):
            ax.add_line(Line2D([x[i],x[i]], [y_top,y_base], color="sienna",linewidth=1.5,zorder=1))
            a = 0.05*1.0/N
            ax.add_line(Line2D([x[i]-a,x[i]+a], [y_top,y_top], color="sienna",linewidth=2.5,zorder=1))
        self.fig =fig
        self.ax=ax
             
        # Initialize the plot with some default data:
        
        # get background to match ambient light.
        # 0=> dark (night-time) and 1=> light (day-time)
        # bound the value between (0.0001, 0.999)
        ambient_light_level = 0
        cmap = cm.get_cmap('bone')
        ax.set_facecolor(cmap(ambient_light_level))
        # insert text to indicate ambient light
        self.text=ax.text(0.5, 0.9, "ambient_light_level = {:.2f}".format(ambient_light_level), backgroundcolor="white",horizontalalignment='center')
        
        
        # Now draw the light orbs according 
        # to the light intensities
        self.base_light_radius = 0.75*1.0/N # base radius for each light orb in full intensity
        base_light_radius = self.base_light_radius
        # wedge angles in degrees
        theta1 = 270-60
        theta2 = 270+60
        for i in range(N):
            circle1 = Wedge((x[i], y_top), 0* base_light_radius,     theta1=theta1, theta2=theta2, color='yellow',alpha=0.2,zorder=2)
            circle2 = Wedge((x[i], y_top), 0* base_light_radius*0.5, theta1=theta1, theta2=theta2, color='yellow',alpha=0.5,zorder=3)
            circle3 = Wedge((x[i], y_top), 0* base_light_radius*0.2, theta1=theta1, theta2=theta2, color='yellow',alpha=1,  zorder=4)
            ax.add_artist(circle1)
            ax.add_artist(circle2)
            ax.add_artist(circle3)
            light = [circle1, circle2, circle3]
            self.lights.append(light)
         
        # Indicate activity using circles for 
        # each detected object
        self.base_obj_radius=min( 0.1/(N+1), 0.03)
        for i in range(N):
                obj = plt.Circle((x[i], y_object), 0.0*self.base_obj_radius, color='blue',alpha=1,zorder=5)
                ax.add_artist(obj)
                self.objects.append(obj)
        
        # Indicate faults using circles for 
        # each detected object
        self.base_fault_radius= min ( 0.2/(N+1), 0.03)
        for i in range(N):
                flt = plt.Circle((x[i], y_fault), 0.0*self.base_fault_radius, color='red',alpha=1,zorder=5)
                ax.add_artist(flt)
                self.faults.append(flt)
     
        # draw the plot
        fig.canvas.draw()
        plt.show()
    
    def update_plot(self, intensities, activities, faults, ambient_light_level):
        
        """
        Update plot
        """
        assert(len(intensities)==self.N)
        assert(len(activities)==self.N)
        assert(self.fig!=None)
        assert(self.ax !=None)
        
        # set ambient light.
        # bound the value between (0.0001, 0.999)
        ambient_light_level = min(0.999, max(0.0001,ambient_light_level))
        cmap = cm.get_cmap('bone')
        self.ax.set_facecolor(cmap(ambient_light_level*0.9))
        self.text.set_text("ambient_light_level = {:.2f}".format(ambient_light_level))
        
        # Update the light orbs according to the intensities
        base_light_radius = self.base_light_radius
        for i in range(self.N):
            light =self.lights[i]
            light[0].set_radius(intensities[i]* base_light_radius)
            light[1].set_radius(intensities[i]* base_light_radius*0.5)
            light[2].set_radius(intensities[i]* base_light_radius*0.2)
            
        # Update activity for each object detected.
        for i in range(self.N):
            obj = self.objects[i]
            # check that activity value is either 0 or 1
            assert(activities[i]==0 or activities[i]==1)
            obj.set_radius(activities[i]*self.base_obj_radius)
        
        # Update fault info for each streetlight
        for i in range(self.N):
            flt = self.faults[i]
            # check that fault value is either 0 or 1
            assert(faults[i]>=0 and faults[i]<=1)
            flt.set_radius(faults[i]*self.base_fault_radius)
        # show the updated plot
        self.fig.canvas.draw()

if __name__=='__main__':
    print("---------------------------------------")
    print(" Streetlight visualization")

    N = 5
    intensities=[0 for i in range (N)]
    activities=[0 for i in range(N)]
    activities[0]=1
    faults=[0 for i in range(N)]
    ambient_light_level = 1

    
    # draw the first plot
    P = PlotStreetlights("Sample_plot",N)
    plt.show()

    # create an animation 
    # by updating the plot periodically
    t_max=100
    for t in range(t_max):
        # wait for a while
        time.sleep(0.05)
        intensities = [t/t_max for i in range (N)]
        activities = activities[-1:] + activities[:-1]
        ambient_light_level = 1 - t/t_max
        # the last light is faulty
        faults[-1]=1
        intensities[-1]=0
        P.update_plot(intensities,activities, faults, ambient_light_level)

    print("done")
    time.sleep(2)
