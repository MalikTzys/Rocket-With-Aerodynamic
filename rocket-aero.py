import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import math
import numpy as np
from collections import deque

class ParticleSystem:
    def __init__(self):
        self.particles = []
        
    def emit(self, position, velocity, count=5):
        for _ in range(count):
            particle = {
                'pos': position.copy() + np.random.randn(3) * 2,
                'vel': velocity + np.random.randn(3) * 5,
                'life': 1.0,
                'size': np.random.uniform(low=0.3, high=0.6)
            }
            self.particles.append(particle)
    
    def update(self, dt):
        for p in self.particles[:]:
            p['pos'] += p['vel'] * dt
            p['vel'] *= 0.95
            p['life'] -= dt * 2
            if p['life'] <= 0:
                self.particles.remove(p)
    
    def draw(self):
        glEnable(GL_POINT_SMOOTH)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE)
        
        for p in self.particles:
            glPointSize(p['size'] * p['life'] * 20)
            alpha = p['life']
            glColor4f(1.0, 0.5 + p['life']*0.5, 0.0, alpha)
            glBegin(GL_POINTS)
            glVertex3f(p['pos'][0]/100, p['pos'][1]/100, p['pos'][2]/100)
            glEnd()
        
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glDisable(GL_POINT_SMOOTH)

class SmokeTrail:
    def __init__(self, max_points=50):
        self.points = deque(maxlen=max_points)
        
    def add_point(self, position):
        self.points.append(position.copy())
    
    def draw(self):
        if len(self.points) < 2:
            return
        
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glLineWidth(4.0)
        glBegin(GL_LINE_STRIP)
        for i, point in enumerate(self.points):
            alpha = i / len(self.points)
            glColor4f(0.6, 0.6, 0.7, alpha * 0.6)
            glVertex3f(point[0]/100, point[1]/100, point[2]/100)
        glEnd()
        glLineWidth(1.0)
        glDisable(GL_BLEND)

class Rocket:
    def __init__(self):
        self.mass = 5000.0
        self.fuel_mass = 3000.0
        self.dry_mass = 2000.0
        self.velocity = np.array([0.0, 0.0, 0.0], dtype=float)
        self.position = np.array([0.0, 500.0, 0.0], dtype=float)
        self.angular_velocity = np.array([0.0, 0.0, 0.0], dtype=float)
        self.thrust = 75000.0
        self.max_thrust = 200000.0
        self.drag_coefficient = 0.45
        self.reference_area = 10.0
        self.engine_temperature = 300.0
        self.structural_stress = 0.0
        self.fuel_consumption_rate = 5.0
        self.max_q = 0.0
        self.trail = SmokeTrail(60)
        self.particles = ParticleSystem()
        
        self.pitch = 0.0
        self.yaw = 0.0
        self.roll = 0.0
        
        self.orientation_matrix = np.eye(3)
        
    def get_rotation_matrix(self):
        pitch_rad = math.radians(self.pitch)
        yaw_rad = math.radians(self.yaw)
        roll_rad = math.radians(self.roll)
        
        cos_p, sin_p = math.cos(pitch_rad), math.sin(pitch_rad)
        cos_y, sin_y = math.cos(yaw_rad), math.sin(yaw_rad)
        cos_r, sin_r = math.cos(roll_rad), math.sin(roll_rad)
        
        Rx = np.array([
            [1, 0, 0],
            [0, cos_p, -sin_p],
            [0, sin_p, cos_p]
        ])
        
        Ry = np.array([
            [cos_y, 0, sin_y],
            [0, 1, 0],
            [-sin_y, 0, cos_y]
        ])
        
        Rz = np.array([
            [cos_r, -sin_r, 0],
            [sin_r, cos_r, 0],
            [0, 0, 1]
        ])
        
        return Ry @ Rx @ Rz
        
    def get_thrust_vector(self):
        local_thrust = np.array([0.0, 1.0, 0.0])
        rotation_matrix = self.get_rotation_matrix()
        return rotation_matrix @ local_thrust
        
    def calculate_drag(self, air_density):
        v_magnitude = np.linalg.norm(self.velocity)
        if v_magnitude > 0.1:
            drag_force_magnitude = 0.5 * air_density * v_magnitude**2 * self.drag_coefficient * self.reference_area
            drag_direction = -self.velocity / v_magnitude
            return drag_force_magnitude * drag_direction
        return np.array([0.0, 0.0, 0.0])
    
    def calculate_lift(self, air_density):
        v_magnitude = np.linalg.norm(self.velocity)
        if v_magnitude > 1.0:
            thrust_dir = self.get_thrust_vector()
            vel_normalized = self.velocity / v_magnitude
            
            cross_product = np.cross(vel_normalized, thrust_dir)
            cross_magnitude = np.linalg.norm(cross_product)
            
            if cross_magnitude > 0.01:
                angle_of_attack = math.asin(min(cross_magnitude, 1.0))
                lift_coefficient = 2 * math.pi * math.sin(angle_of_attack)
                lift_magnitude = 0.5 * air_density * v_magnitude**2 * abs(lift_coefficient) * self.reference_area
                
                lift_direction = np.cross(self.velocity, cross_product)
                lift_dir_magnitude = np.linalg.norm(lift_direction)
                if lift_dir_magnitude > 0:
                    lift_direction = lift_direction / lift_dir_magnitude
                    return lift_magnitude * lift_direction
        
        return np.array([0.0, 0.0, 0.0])
    
    def calculate_dynamic_pressure(self, air_density):
        v_magnitude = np.linalg.norm(self.velocity)
        return 0.5 * air_density * v_magnitude**2
    
    def get_angle_of_attack(self):
        v_magnitude = np.linalg.norm(self.velocity)
        if v_magnitude > 0.1:
            thrust_dir = self.get_thrust_vector()
            vel_normalized = self.velocity / v_magnitude
            dot_product = np.dot(thrust_dir, vel_normalized)
            return math.degrees(math.acos(np.clip(dot_product, -1.0, 1.0)))
        return 0.0
    
    def update(self, dt, air_density, gravity):
        if dt <= 0:
            return self.get_telemetry()
            
        self.trail.add_point(self.position)
        
        if self.thrust > 0 and self.fuel_mass > 0:
            fuel_used = self.fuel_consumption_rate * dt
            self.fuel_mass = max(0, self.fuel_mass - fuel_used)
            self.mass = self.dry_mass + self.fuel_mass
            
            if self.fuel_mass <= 0:
                self.thrust = 0
        else:
            self.mass = self.dry_mass + self.fuel_mass
        
        self.pitch += self.angular_velocity[0] * dt
        self.yaw += self.angular_velocity[1] * dt
        self.roll += self.angular_velocity[2] * dt
        
        self.pitch = self.pitch % 360
        self.yaw = self.yaw % 360
        self.roll = self.roll % 360
        
        self.angular_velocity *= 0.92
        
        thrust_direction = self.get_thrust_vector()
        
        drag = self.calculate_drag(air_density)
        lift = self.calculate_lift(air_density)
        thrust_vector = self.thrust * thrust_direction
        gravity_force = np.array([0.0, -gravity * self.mass, 0.0])
        
        total_force = thrust_vector + drag + lift + gravity_force
        
        if self.mass > 0:
            acceleration = total_force / self.mass
        else:
            acceleration = np.array([0.0, 0.0, 0.0])
        
        dynamic_pressure = self.calculate_dynamic_pressure(air_density)
        self.max_q = max(self.max_q, dynamic_pressure)
        
        force_magnitude = np.linalg.norm(total_force)
        if self.mass > 0:
            self.structural_stress = (force_magnitude / self.mass) / 9.81
        else:
            self.structural_stress = 0
        
        self.engine_temperature = 300 + (self.thrust / self.max_thrust) * 2000
        
        self.velocity += acceleration * dt
        self.position += self.velocity * dt
        
        if self.position[1] < 0:
            self.position[1] = 0
            if self.velocity[1] < 0:
                self.velocity[1] = -self.velocity[1] * 0.3
                self.velocity[0] *= 0.7
                self.velocity[2] *= 0.7
        
        if self.thrust > 0:
            exhaust_velocity = -thrust_direction * 100 + self.velocity
            exhaust_pos = self.position - thrust_direction * 400
            self.particles.emit(exhaust_pos, exhaust_velocity, 4)
        
        self.particles.update(dt)
        
        return self.get_telemetry()
    
    def get_telemetry(self):
        v_magnitude = np.linalg.norm(self.velocity)
        mach_number = v_magnitude / 343.0
        thrust_direction = self.get_thrust_vector()
        
        drag = self.calculate_drag(1.225)
        lift = self.calculate_lift(1.225)
        thrust_vector = self.thrust * thrust_direction
        
        aoa = self.get_angle_of_attack()
        dynamic_pressure = self.calculate_dynamic_pressure(1.225)
        
        twr = 0
        if self.mass > 0:
            twr = self.thrust / (self.mass * 9.81)
        
        return {
            'drag': np.linalg.norm(drag),
            'lift': np.linalg.norm(lift),
            'thrust': np.linalg.norm(thrust_vector),
            'velocity': v_magnitude,
            'altitude': self.position[1],
            'aoa': aoa,
            'dynamic_pressure': dynamic_pressure,
            'max_q': self.max_q,
            'g_force': self.structural_stress,
            'temperature': self.engine_temperature,
            'fuel': self.fuel_mass,
            'twr': twr,
            'mach': mach_number,
            'thrust_direction': thrust_direction
        }

def draw_rocket(rocket, wireframe=False):
    glPushMatrix()
    glTranslatef(rocket.position[0]/100, rocket.position[1]/100, rocket.position[2]/100)
    
    glRotatef(rocket.yaw, 0, 1, 0)
    glRotatef(rocket.pitch, 1, 0, 0)
    glRotatef(rocket.roll, 0, 0, 1)
    
    scale = 2.0
    glScalef(scale, scale, scale)
    
    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)
    glEnable(GL_COLOR_MATERIAL)
    glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
    
    light_position = [5.0, 10.0, 5.0, 1.0]
    light_ambient = [0.3, 0.3, 0.3, 1.0]
    light_diffuse = [0.8, 0.8, 0.8, 1.0]
    glLightfv(GL_LIGHT0, GL_POSITION, light_position)
    glLightfv(GL_LIGHT0, GL_AMBIENT, light_ambient)
    glLightfv(GL_LIGHT0, GL_DIFFUSE, light_diffuse)
    
    if wireframe:
        glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
        glDisable(GL_LIGHTING)
    
    heat_factor = min(rocket.engine_temperature / 2300.0, 1.0)
    base_color = (0.9, 0.1, 0.1)
    hot_color = (1.0, 0.4, 0.0)
    color = tuple(base_color[i] * (1-heat_factor) + hot_color[i] * heat_factor for i in range(3))
    
    glColor3f(*color)
    glBegin(GL_TRIANGLE_FAN)
    glNormal3f(0, 1, 0)
    glVertex3f(0, 2.2, 0)
    for i in range(17):
        angle = i * math.pi / 8
        nx = math.cos(angle)
        nz = math.sin(angle)
        glNormal3f(nx, 0.5, nz)
        glVertex3f(0.3 * nx, 1.5, 0.3 * nz)
    glEnd()
    
    glColor3f(0.85, 0.85, 0.95)
    glBegin(GL_QUAD_STRIP)
    for i in range(17):
        angle = i * math.pi / 8
        u = i / 16.0
        shade = 0.85 + 0.15 * math.sin(u * math.pi * 4)
        glColor3f(shade, shade, shade + 0.1)
        nx = math.cos(angle)
        nz = math.sin(angle)
        glNormal3f(nx, 0, nz)
        glVertex3f(0.3 * nx, 1.5, 0.3 * nz)
        glVertex3f(0.35 * nx, 0, 0.35 * nz)
    glEnd()
    
    glColor3f(0.75, 0.75, 0.8)
    glBegin(GL_QUAD_STRIP)
    for i in range(17):
        angle = i * math.pi / 8
        nx = math.cos(angle)
        nz = math.sin(angle)
        glNormal3f(nx, 0, nz)
        glVertex3f(0.35 * nx, 0, 0.35 * nz)
        glVertex3f(0.3 * nx, -1.5, 0.3 * nz)
    glEnd()
    
    glColor3f(0.2, 0.2, 0.25)
    glBegin(GL_TRIANGLE_FAN)
    glNormal3f(0, -1, 0)
    glVertex3f(0, -1.5, 0)
    for i in range(17):
        angle = i * math.pi / 8
        glVertex3f(0.3 * math.cos(angle), -1.5, 0.3 * math.sin(angle))
    glEnd()
    
    for j in range(4):
        fin_angle = j * math.pi / 2
        glPushMatrix()
        glRotatef(math.degrees(fin_angle), 0, 1, 0)
        
        glColor3f(0.3, 0.3, 0.35)
        glBegin(GL_TRIANGLES)
        glNormal3f(0, 0, -1)
        glVertex3f(0.3, -1.2, 0)
        glVertex3f(0.9, -2.2, 0)
        glVertex3f(0.3, -2.2, 0)
        glEnd()
        
        glColor3f(0.25, 0.25, 0.3)
        glBegin(GL_TRIANGLES)
        glNormal3f(0.7, 0, 0.7)
        glVertex3f(0.3, -1.2, 0)
        glVertex3f(0.9, -2.2, 0)
        glVertex3f(0.3, -2.2, 0.05)
        glEnd()
        
        glPopMatrix()
    
    if rocket.thrust > 0:
        glDisable(GL_LIGHTING)
        thrust_intensity = rocket.thrust / rocket.max_thrust
        
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE)
        
        for layer in range(3):
            offset = layer * 0.5
            alpha = (1.0 - layer * 0.3) * thrust_intensity
            
            glColor4f(1.0, 0.8 - layer*0.2, 0.2 - layer*0.1, alpha)
            glBegin(GL_TRIANGLE_FAN)
            glVertex3f(0, -2.5 - offset, 0)
            for i in range(17):
                angle = i * math.pi / 8
                radius = 0.25 * (1 + layer * 0.5)
                glVertex3f(radius * math.cos(angle), -2.2, radius * math.sin(angle))
            glEnd()
        
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glDisable(GL_BLEND)
        
        if not wireframe:
            glEnable(GL_LIGHTING)
    
    glDisable(GL_LIGHTING)
    glDisable(GL_COLOR_MATERIAL)
    
    if wireframe:
        glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
    
    glPopMatrix()
    
    rocket.trail.draw()
    rocket.particles.draw()

def draw_vector(origin, direction, magnitude, color, scale=0.01, label=""):
    if magnitude < 0.1:
        return
    
    glDisable(GL_LIGHTING)
    glColor3f(*color)
    glLineWidth(5.0)
    glBegin(GL_LINES)
    glVertex3f(origin[0]/100, origin[1]/100, origin[2]/100)
    end = origin + direction * magnitude * scale
    glVertex3f(end[0]/100, end[1]/100, end[2]/100)
    glEnd()
    
    arrow_size = 0.4
    perp1 = np.array([-direction[1], direction[0], 0])
    if np.linalg.norm(perp1) > 0:
        perp1 = perp1 / np.linalg.norm(perp1) * arrow_size
    perp2 = np.cross(direction, perp1)
    if np.linalg.norm(perp2) > 0:
        perp2 = perp2 / np.linalg.norm(perp2) * arrow_size
    
    glBegin(GL_TRIANGLES)
    glVertex3f(end[0]/100, end[1]/100, end[2]/100)
    back = end - direction * arrow_size * 2
    glVertex3f((back[0] + perp1[0])/100, (back[1] + perp1[1])/100, (back[2] + perp1[2])/100)
    glVertex3f((back[0] - perp1[0])/100, (back[1] - perp1[1])/100, (back[2] - perp1[2])/100)
    glEnd()
    
    glLineWidth(1.0)

def draw_atmosphere(altitude, display):
    if altitude < 0:
        altitude = 0
    
    sky_color_low = np.array([0.53, 0.81, 0.92])
    sky_color_high = np.array([0.0, 0.0, 0.1])
    
    blend = min(altitude / 50000.0, 1.0)
    sky_color = sky_color_low * (1 - blend) + sky_color_high * blend
    
    glClearColor(*sky_color, 1.0)

def draw_infinite_grid(rocket_pos):
    glDisable(GL_LIGHTING)
    glLineWidth(1.0)
    
    grid_size = 500
    grid_spacing = 50
    
    grid_x_center = round(rocket_pos[0] / grid_spacing) * grid_spacing
    grid_z_center = round(rocket_pos[2] / grid_spacing) * grid_spacing
    
    grid_range = 50
    
    for i in range(-grid_range, grid_range + 1):
        x_pos = grid_x_center + i * grid_spacing
        
        if abs(x_pos) < 10:
            glColor3f(0.5, 0.2, 0.2)
            glLineWidth(3.0)
        elif i % 5 == 0:
            glColor3f(0.3, 0.3, 0.4)
            glLineWidth(2.0)
        else:
            glColor3f(0.15, 0.15, 0.2)
            glLineWidth(1.0)
        
        glBegin(GL_LINES)
        glVertex3f(x_pos, 0, grid_z_center - grid_range * grid_spacing)
        glVertex3f(x_pos, 0, grid_z_center + grid_range * grid_spacing)
        glEnd()
    
    for i in range(-grid_range, grid_range + 1):
        z_pos = grid_z_center + i * grid_spacing
        
        if abs(z_pos) < 10:
            glColor3f(0.2, 0.2, 0.5)
            glLineWidth(3.0)
        elif i % 5 == 0:
            glColor3f(0.3, 0.3, 0.4)
            glLineWidth(2.0)
        else:
            glColor3f(0.15, 0.15, 0.2)
            glLineWidth(1.0)
        
        glBegin(GL_LINES)
        glVertex3f(grid_x_center - grid_range * grid_spacing, 0, z_pos)
        glVertex3f(grid_x_center + grid_range * grid_spacing, 0, z_pos)
        glEnd()
    
    glLineWidth(4.0)
    glBegin(GL_LINES)
    glColor3f(1, 0, 0)
    glVertex3f(0, 0, 0)
    glVertex3f(1000, 0, 0)
    glColor3f(0, 1, 0)
    glVertex3f(0, 0, 0)
    glVertex3f(0, 1000, 0)
    glColor3f(0, 0, 1)
    glVertex3f(0, 0, 0)
    glVertex3f(0, 0, 1000)
    glEnd()
    glLineWidth(1.0)

def draw_text_2d(x, y, text, font, color=(0, 255, 100)):
    text_surface = font.render(text, True, color)
    text_data = pygame.image.tostring(text_surface, "RGBA", True)
    glWindowPos2d(x, y)
    glDrawPixels(text_surface.get_width(), text_surface.get_height(), 
                 GL_RGBA, GL_UNSIGNED_BYTE, text_data)

def draw_rounded_rect(x, y, width, height, radius, color):
    glColor4f(*color)
    glBegin(GL_POLYGON)
    glVertex2f(x + radius, y)
    glVertex2f(x + width - radius, y)
    glVertex2f(x + width - radius, y + height)
    glVertex2f(x + radius, y + height)
    glEnd()
    
    glBegin(GL_POLYGON)
    glVertex2f(x, y + radius)
    glVertex2f(x + radius, y + radius)
    glVertex2f(x + radius, y + height - radius)
    glVertex2f(x, y + height - radius)
    glEnd()
    
    glBegin(GL_POLYGON)
    glVertex2f(x + width - radius, y + radius)
    glVertex2f(x + width, y + radius)
    glVertex2f(x + width, y + height - radius)
    glVertex2f(x + width - radius, y + height - radius)
    glEnd()

def draw_info_card(x, y, width, height, title, value, unit, color, font, font_small):
    draw_rounded_rect(x, y, width, height, 5, (0.08, 0.08, 0.15, 0.9))
    
    glColor4f(*color, 1.0)
    glBegin(GL_QUADS)
    glVertex2f(x, y)
    glVertex2f(x + 4, y)
    glVertex2f(x + 4, y + height)
    glVertex2f(x, y + height)
    glEnd()
    
    draw_text_2d(x + 10, y + height - 22, title, font_small, (180, 180, 200))
    
    value_text = f"{value:.1f}" if isinstance(value, float) else str(value)
    color_rgb = tuple(int(c * 255) for c in color[:3])
    draw_text_2d(x + 10, y + height - 48, value_text, font, color_rgb)
    
    if unit:
        draw_text_2d(x + 10, y + height - 70, unit, font_small, (150, 150, 170))

def draw_progress_bar(x, y, width, height, value, max_value, color, label, font):
    percentage = min(value / max_value, 1.0) if max_value > 0 else 0
    
    draw_rounded_rect(x, y, width, height, 4, (0.1, 0.1, 0.15, 0.8))
    
    if percentage > 0:
        fill_width = width * percentage
        glColor3f(*color)
        glBegin(GL_QUADS)
        glVertex2f(x, y)
        glVertex2f(x + fill_width, y)
        glVertex2f(x + fill_width, y + height)
        glVertex2f(x, y + height)
        glEnd()
    
    glColor3f(0.5, 0.5, 0.5)
    glLineWidth(2.0)
    glBegin(GL_LINE_LOOP)
    glVertex2f(x, y)
    glVertex2f(x + width, y)
    glVertex2f(x + width, y + height)
    glVertex2f(x, y + height)
    glEnd()
    
    text = f"{label}: {value:.0f}/{max_value:.0f} ({percentage*100:.0f}%)"
    draw_text_2d(x + 10, y + height//2 - 6, text, font, (255, 255, 255))

def draw_settings_panel(display, rocket, air_density, show_vectors, show_wireframe, auto_rotate, time_scale, font, font_small):
    screen_width, screen_height = display
    panel_width = min(500, screen_width - 40)
    panel_height = min(600, screen_height - 40)
    panel_x = screen_width//2 - panel_width//2
    panel_y = screen_height//2 - panel_height//2
    
    glColor4f(0.05, 0.05, 0.1, 0.95)
    glBegin(GL_QUADS)
    glVertex2f(panel_x, panel_y)
    glVertex2f(panel_x + panel_width, panel_y)
    glVertex2f(panel_x + panel_width, panel_y + panel_height)
    glVertex2f(panel_x, panel_y + panel_height)
    glEnd()
    
    glColor3f(0.3, 0.5, 0.8)
    glLineWidth(3.0)
    glBegin(GL_LINE_LOOP)
    glVertex2f(panel_x, panel_y)
    glVertex2f(panel_x + panel_width, panel_y)
    glVertex2f(panel_x + panel_width, panel_y + panel_height)
    glVertex2f(panel_x, panel_y + panel_height)
    glEnd()
    
    y_offset = panel_y + panel_height - 40
    
    draw_text_2d(panel_x + 20, y_offset, "PENGATURAN SIMULASI", font, (100, 200, 255))
    y_offset -= 50
    
    draw_text_2d(panel_x + 20, y_offset, "PARAMETER ROKET", font_small, (255, 200, 100))
    y_offset -= 30
    draw_text_2d(panel_x + 30, y_offset, f"Massa: {rocket.dry_mass:.0f} kg [W/S]", font_small)
    y_offset -= 25
    draw_text_2d(panel_x + 30, y_offset, f"Thrust: {rocket.thrust:.0f} N [A/D]", font_small)
    y_offset -= 25
    draw_text_2d(panel_x + 30, y_offset, f"Max Thrust: {rocket.max_thrust:.0f} N", font_small)
    y_offset -= 40
    
    draw_text_2d(panel_x + 20, y_offset, "KONTROL", font_small, (255, 150, 255))
    y_offset -= 30
    draw_text_2d(panel_x + 30, y_offset, "Arrow Keys: Pitch/Yaw", font_small)
    y_offset -= 25
    draw_text_2d(panel_x + 30, y_offset, "1/2: Roll", font_small)
    y_offset -= 40
    
    draw_text_2d(panel_x + 20, y_offset, "TAMPILAN", font_small, (150, 200, 255))
    y_offset -= 30
    status = "ON" if show_vectors else "OFF"
    color = (100, 255, 100) if show_vectors else (255, 100, 100)
    draw_text_2d(panel_x + 30, y_offset, f"Vektor: {status} [V]", font_small, color)
    y_offset -= 25
    status = "ON" if show_wireframe else "OFF"
    color = (100, 255, 100) if show_wireframe else (255, 100, 100)
    draw_text_2d(panel_x + 30, y_offset, f"Wireframe: {status} [F]", font_small, color)
    y_offset -= 40
    
    draw_text_2d(panel_x + 20, y_offset, "SIMULASI", font_small, (255, 255, 100))
    y_offset -= 30
    draw_text_2d(panel_x + 30, y_offset, f"Kecepatan: {time_scale:.1f}x [+/-]", font_small)
    y_offset -= 25
    draw_text_2d(panel_x + 30, y_offset, "Pause: [SPACE]", font_small)
    y_offset -= 25
    draw_text_2d(panel_x + 30, y_offset, "Reset: [R]", font_small)
    y_offset -= 40
    
    draw_text_2d(panel_x + panel_width//2 - 100, panel_y + 20, "Tekan TAB untuk menutup", font_small, (200, 200, 200))

def main():
    pygame.init()
    info = pygame.display.Info()
    display = (min(1600, info.current_w - 100), min(1000, info.current_h - 100))
    screen = pygame.display.set_mode(display, DOUBLEBUF | OPENGL)
    pygame.display.set_caption("Simulasi Aerodinamika Roket 3D - Fisika Sempurna")
    
    glEnable(GL_DEPTH_TEST)
    glDepthFunc(GL_LEQUAL)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glEnable(GL_LINE_SMOOTH)
    glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)
    glEnable(GL_NORMALIZE)
    glShadeModel(GL_SMOOTH)
    
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(50, (display[0] / display[1]), 0.1, 500.0)
    
    glMatrixMode(GL_MODELVIEW)
    
    font_size_large = max(24, min(36, display[1] // 30))
    font_size = max(18, min(28, display[1] // 40))
    font_size_small = max(14, min(22, display[1] // 50))
    
    font_large = pygame.font.Font(None, font_size_large)
    font = pygame.font.Font(None, font_size)
    font_small = pygame.font.Font(None, font_size_small)
    
    rocket = Rocket()
    clock = pygame.time.Clock()
    
    camera_distance = 45.0
    camera_rotation_x = 20
    camera_rotation_y = 45
    mouse_down = False
    last_mouse_pos = (0, 0)
    
    air_density = 1.225
    gravity = 9.81
    show_vectors = True
    show_wireframe = False
    paused = False
    time_scale = 1.0
    auto_rotate = False
    show_settings = False
    
    running = True
    while running:
        dt = clock.tick(60) / 1000.0
        if not paused:
            dt *= time_scale
        else:
            dt = 0
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == MOUSEBUTTONDOWN:
                if event.button == 1:
                    mouse_down = True
                    last_mouse_pos = pygame.mouse.get_pos()
                elif event.button == 4:
                    camera_distance = max(10, camera_distance - 3)
                elif event.button == 5:
                    camera_distance = min(200, camera_distance + 3)
            elif event.type == MOUSEBUTTONUP:
                if event.button == 1:
                    mouse_down = False
            elif event.type == MOUSEMOTION:
                if mouse_down:
                    current_pos = pygame.mouse.get_pos()
                    dx = current_pos[0] - last_mouse_pos[0]
                    dy = current_pos[1] - last_mouse_pos[1]
                    camera_rotation_y += dx * 0.5
                    camera_rotation_x += dy * 0.5
                    camera_rotation_x = max(-89, min(89, camera_rotation_x))
                    last_mouse_pos = current_pos
            elif event.type == KEYDOWN:
                if event.key == K_TAB:
                    show_settings = not show_settings
                elif event.key == K_v:
                    show_vectors = not show_vectors
                elif event.key == K_f:
                    show_wireframe = not show_wireframe
                elif event.key == K_SPACE:
                    paused = not paused
                elif event.key == K_r:
                    rocket = Rocket()
                    camera_rotation_x = 20
                    camera_rotation_y = 45
                    camera_distance = 45.0
                elif event.key == K_EQUALS or event.key == K_PLUS:
                    time_scale = min(time_scale * 1.5, 5.0)
                elif event.key == K_MINUS:
                    time_scale = max(time_scale / 1.5, 0.1)
                elif event.key == K_c:
                    auto_rotate = not auto_rotate
        
        keys = pygame.key.get_pressed()
        
        rotation_speed = 30.0
        if keys[K_UP]:
            rocket.angular_velocity[0] -= rotation_speed * (clock.get_time() / 1000.0) * 10
        if keys[K_DOWN]:
            rocket.angular_velocity[0] += rotation_speed * (clock.get_time() / 1000.0) * 10
        if keys[K_LEFT]:
            rocket.angular_velocity[1] -= rotation_speed * (clock.get_time() / 1000.0) * 10
        if keys[K_RIGHT]:
            rocket.angular_velocity[1] += rotation_speed * (clock.get_time() / 1000.0) * 10
        
        if keys[K_1]:
            rocket.angular_velocity[2] -= rotation_speed * (clock.get_time() / 1000.0) * 10
        if keys[K_2]:
            rocket.angular_velocity[2] += rotation_speed * (clock.get_time() / 1000.0) * 10
        
        if keys[K_w]:
            rocket.dry_mass = max(500, rocket.dry_mass - 20)
            rocket.mass = rocket.dry_mass + rocket.fuel_mass
        if keys[K_s]:
            rocket.dry_mass = min(10000, rocket.dry_mass + 20)
            rocket.mass = rocket.dry_mass + rocket.fuel_mass
        if keys[K_a]:
            rocket.thrust = max(0, rocket.thrust - 1000)
        if keys[K_d]:
            rocket.thrust = min(rocket.max_thrust, rocket.thrust + 1000)
        if keys[K_q]:
            air_density = max(0.01, air_density - 0.02)
        if keys[K_e]:
            air_density = min(5.0, air_density + 0.02)
        if keys[K_z]:
            rocket.drag_coefficient = max(0.1, rocket.drag_coefficient - 0.02)
        if keys[K_x]:
            rocket.drag_coefficient = min(2.0, rocket.drag_coefficient + 0.02)
        
        if auto_rotate:
            camera_rotation_y += 10 * (clock.get_time() / 1000.0)
        
        telemetry = rocket.update(dt, air_density, gravity)
        
        draw_atmosphere(telemetry['altitude'], display)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        
        cam_x = math.sin(math.radians(camera_rotation_y)) * math.cos(math.radians(camera_rotation_x)) * camera_distance
        cam_y = math.sin(math.radians(camera_rotation_x)) * camera_distance
        cam_z = math.cos(math.radians(camera_rotation_y)) * math.cos(math.radians(camera_rotation_x)) * camera_distance
        
        rocket_pos_world = rocket.position / 100.0
        
        gluLookAt(
            rocket_pos_world[0] + cam_x, rocket_pos_world[1] + cam_y, rocket_pos_world[2] + cam_z,
            rocket_pos_world[0], rocket_pos_world[1], rocket_pos_world[2],
            0, 1, 0
        )
        
        draw_infinite_grid(rocket.position)
        draw_rocket(rocket, show_wireframe)
        
        if show_vectors and not paused:
            if np.linalg.norm(rocket.velocity) > 0.1:
                drag_dir = -rocket.velocity / np.linalg.norm(rocket.velocity)
                draw_vector(rocket.position, drag_dir, telemetry['drag'], (1, 0.3, 0.3), 0.005)
            
            thrust_dir = telemetry['thrust_direction']
            draw_vector(rocket.position, thrust_dir, telemetry['thrust'], (0.3, 1, 0.3), 0.001)
            
            if telemetry['lift'] > 10:
                lift_dir = np.array([0, 1, 0])
                draw_vector(rocket.position, lift_dir, telemetry['lift'], (0.3, 0.6, 1), 0.005)
            
            if np.linalg.norm(rocket.velocity) > 1:
                vel_dir = rocket.velocity / np.linalg.norm(rocket.velocity)
                draw_vector(rocket.position, vel_dir, np.linalg.norm(rocket.velocity), (1, 1, 0.3), 0.1)
        
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, display[0], 0, display[1], -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        glDisable(GL_DEPTH_TEST)
        
        if not show_settings:
            card_width = min(150, display[0] // 11)
            card_height = min(70, display[1] // 14)
            card_spacing = 8
            start_x = 15
            start_y = display[1] - card_height - 15
            
            cards = [
                ("KECEPATAN", telemetry['velocity'], "m/s", (0.3, 1.0, 0.3)),
                ("KETINGGIAN", telemetry['altitude'], "m", (0.3, 0.6, 1.0)),
                ("MACH", telemetry['mach'], "", (1.0, 0.5, 0.3)),
                ("MASSA", rocket.mass, "kg", (0.8, 0.8, 0.3)),
            ]
            
            for i, (title, value, unit, color) in enumerate(cards):
                row = i // 2
                col = i % 2
                x = start_x + col * (card_width + card_spacing)
                y = start_y - row * (card_height + card_spacing)
                draw_info_card(x, y, card_width, card_height, title, value, unit, color, font, font_small)
            
            start_y = display[1] - card_height * 2 - card_spacing * 2 - 15
            cards2 = [
                ("TWR", telemetry['twr'], "", (1.0, 0.7, 0.3)),
                ("G-FORCE", telemetry['g_force'], "g", (1.0, 0.3, 0.3)),
                ("DRAG", telemetry['drag'], "N", (1.0, 0.4, 0.4)),
                ("LIFT", telemetry['lift'], "N", (0.4, 0.7, 1.0)),
            ]
            
            for i, (title, value, unit, color) in enumerate(cards2):
                row = i // 2
                col = i % 2
                x = start_x + col * (card_width + card_spacing)
                y = start_y - row * (card_height + card_spacing)
                draw_info_card(x, y, card_width, card_height, title, value, unit, color, font, font_small)
            
            start_y = display[1] - card_height * 4 - card_spacing * 4 - 15
            cards3 = [
                ("MAX-Q", telemetry['max_q'], "Pa", (1.0, 0.5, 0.9)),
                ("DYN PRESS", telemetry['dynamic_pressure'], "Pa", (0.8, 0.5, 1.0)),
                ("SUHU", telemetry['temperature'], "K", (1.0, 0.6, 0.3)),
                ("AoA", telemetry['aoa'], "°", (0.6, 0.9, 1.0)),
            ]
            
            for i, (title, value, unit, color) in enumerate(cards3):
                row = i // 2
                col = i % 2
                x = start_x + col * (card_width + card_spacing)
                y = start_y - row * (card_height + card_spacing)
                draw_info_card(x, y, card_width, card_height, title, value, unit, color, font, font_small)
            
            bar_width = min(320, display[0] // 5)
            bar_height = min(25, display[1] // 40)
            draw_progress_bar(15, 100, bar_width, bar_height, rocket.fuel_mass, 3000, (0.3, 0.7, 1.0), "FUEL", font_small)
            draw_progress_bar(15, 65, bar_width, bar_height, rocket.thrust, rocket.max_thrust, (1.0, 0.6, 0.2), "THRUST", font_small)
            
            orient_width = min(450, display[0] // 3.5)
            orient_height = min(70, display[1] // 14)
            glColor4f(0.08, 0.08, 0.15, 0.9)
            glBegin(GL_QUADS)
            glVertex2f(15, 10)
            glVertex2f(15 + orient_width, 10)
            glVertex2f(15 + orient_width, 10 + orient_height)
            glVertex2f(15, 10 + orient_height)
            glEnd()
            
            draw_text_2d(25, 55, f"P:{rocket.pitch:.1f}° Y:{rocket.yaw:.1f}° R:{rocket.roll:.1f}°", 
                        font_small, (150, 255, 200))
            draw_text_2d(25, 35, f"Pos: X:{rocket.position[0]:.0f} Y:{rocket.position[1]:.0f} Z:{rocket.position[2]:.0f}", 
                        font_small, (200, 200, 150))
            draw_text_2d(25, 15, "Orientasi & Posisi", font_small, (100, 200, 255))
            
            help_width = min(220, display[0] // 7)
            help_x = display[0] - help_width - 15
            help_height = min(180, display[1] // 5.5)
            
            glColor4f(0.08, 0.08, 0.15, 0.9)
            glBegin(GL_QUADS)
            glVertex2f(help_x, display[1] - help_height)
            glVertex2f(display[0] - 15, display[1] - help_height)
            glVertex2f(display[0] - 15, display[1] - 15)
            glVertex2f(help_x, display[1] - 15)
            glEnd()
            
            y_offset = display[1] - 35
            draw_text_2d(help_x + 10, y_offset, "KONTROL", font, (100, 200, 255))
            y_offset -= 25
            draw_text_2d(help_x + 10, y_offset, "TAB: Pengaturan", font_small, (255, 255, 100))
            y_offset -= 20
            draw_text_2d(help_x + 10, y_offset, "Arrow: Pitch/Yaw", font_small)
            y_offset -= 18
            draw_text_2d(help_x + 10, y_offset, "1/2: Roll", font_small)
            y_offset -= 18
            draw_text_2d(help_x + 10, y_offset, "A/D: Thrust", font_small)
            y_offset -= 18
            draw_text_2d(help_x + 10, y_offset, "SPACE: Pause", font_small)
            y_offset -= 18
            draw_text_2d(help_x + 10, y_offset, "R: Reset", font_small)
            
            status_width = min(250, display[0] // 6.4)
            status_height = min(35, display[1] // 28)
            glColor4f(0.08, 0.08, 0.15, 0.9)
            glBegin(GL_QUADS)
            glVertex2f(display[0]//2 - status_width//2, 10)
            glVertex2f(display[0]//2 + status_width//2, 10)
            glVertex2f(display[0]//2 + status_width//2, 10 + status_height)
            glVertex2f(display[0]//2 - status_width//2, 10 + status_height)
            glEnd()
            
            status_text = "PAUSED" if paused else f"RUNNING {time_scale:.1f}x"
            status_color = (255, 150, 100) if paused else (100, 255, 150)
            text_x = display[0]//2 - len(status_text) * 4
            draw_text_2d(text_x, 18, status_text, font, status_color)
            
            warning_y = display[1]//2
            if rocket.fuel_mass <= 0:
                draw_text_2d(display[0]//2 - 120, warning_y, "FUEL HABIS!", font_large, (255, 80, 80))
                warning_y -= 35
            
            if telemetry['g_force'] > 8:
                draw_text_2d(display[0]//2 - 140, warning_y, "G-FORCE TINGGI!", font, (255, 100, 0))
                warning_y -= 30
            
            if telemetry['dynamic_pressure'] > 50000:
                draw_text_2d(display[0]//2 - 150, warning_y, "TEKANAN KRITIS!", font, (255, 150, 0))
        
        else:
            draw_settings_panel(display, rocket, air_density, show_vectors, show_wireframe, 
                              auto_rotate, time_scale, font, font_small)
        
        glEnable(GL_DEPTH_TEST)
        glPopMatrix()
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        
        pygame.display.flip()
    
    pygame.quit()

if __name__ == "__main__":
    main()
