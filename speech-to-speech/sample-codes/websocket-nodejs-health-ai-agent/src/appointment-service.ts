// appointment-service.ts

// Types for appointment functionality
export interface Doctor {
  id: string;
  name: string;
  specialty: string;
  availability?: AvailabilitySlot[];
}

export interface AvailabilitySlot {
  date: string;
  times: string[];
}

export interface Appointment {
  id: string;
  doctorId: string;
  patientName: string;
  date: string;
  time: string;
  reason: string;
}

export interface AppointmentResult {
  success: boolean;
  message?: string;
  appointment?: Appointment;
  error?: string;
}

// Appointment Service class
export class AppointmentService {
  private doctors: Doctor[] = [
    {
      id: "doc1",
      name: "Dr. Sarah Chen",
      specialty: "Family Medicine",
      availability: [
        { date: "2025-05-16", times: ["09:00", "10:00", "14:00", "15:00"] },
        { date: "2025-05-17", times: ["09:00", "10:00", "11:00"] },
        { date: "2025-05-20", times: ["13:00", "14:00", "15:00", "16:00"] }
      ]
    },
    {
      id: "doc2",
      name: "Dr. Michael Rodriguez",
      specialty: "Cardiology",
      availability: [
        { date: "2025-05-15", times: ["11:00", "13:00", "16:00"] },
        { date: "2025-05-18", times: ["09:00", "10:00", "11:00", "13:00"] },
        { date: "2025-05-19", times: ["14:00", "15:00"] }
      ]
    },
    {
      id: "doc3",
      name: "Dr. Emily Johnson",
      specialty: "Pediatrics",
      availability: [
        { date: "2025-05-15", times: ["09:00", "10:00", "15:00", "16:00"] },
        { date: "2025-05-16", times: ["11:00", "13:00", "14:00"] },
        { date: "2025-05-19", times: ["09:00", "10:00", "11:00"] }
      ]
    }
  ];

  private appointments: Appointment[] = [
    {
      id: "apt1",
      doctorId: "doc1",
      patientName: "John Smith",
      date: "2025-05-16",
      time: "11:00",
      reason: "Annual checkup"
    },
    {
      id: "apt2",
      doctorId: "doc2",
      patientName: "Emma Wilson",
      date: "2025-05-15",
      time: "14:00",
      reason: "Blood pressure follow-up"
    },
    {
      id: "apt3",
      doctorId: "doc3",
      patientName: "Aiden Martinez",
      date: "2025-05-15",
      time: "11:00",
      reason: "Vaccination"
    }
  ];

  // Singleton instance
  private static instance: AppointmentService;

  // Private constructor for singleton pattern
  private constructor() {}

  // Get singleton instance
  public static getInstance(): AppointmentService {
    if (!AppointmentService.instance) {
      AppointmentService.instance = new AppointmentService();
    }
    return AppointmentService.instance;
  }

  // Format calendar for availability display
  public formatAvailabilityCalendar(availability: AvailabilitySlot[]): string {
    if (!availability || availability.length === 0) {
      return "No available slots found.";
    }
    
    const calendarRows = availability.map(slot => {
      const date = new Date(slot.date);
      const formattedDate = date.toLocaleDateString('en-US', { 
        weekday: 'long', 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric' 
      });
      
      const timeSlots = slot.times.map(time => `${time}`).join(' | ');
      
      return `| ${formattedDate} | ${timeSlots} |`;
    });
    
    const header = `| Date | Available Times |\n| ---- | --------------- |`;
    return `${header}\n${calendarRows.join('\n')}`;
  }

  // Format calendar for appointments display
  public formatAppointmentsCalendar(appointments: Appointment[]): string {
    if (!appointments || appointments.length === 0) {
      return "No appointments found.";
    }
    
    // Sort appointments by date and time
    const sortedAppointments = [...appointments].sort((a, b) => {
      const dateCompare = a.date.localeCompare(b.date);
      return dateCompare !== 0 ? dateCompare : a.time.localeCompare(b.time);
    });
    
    const rows = sortedAppointments.map(apt => {
      const date = new Date(apt.date);
      const formattedDate = date.toLocaleDateString('en-US', { 
        weekday: 'long', 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric' 
      });
      
      const doctor = this.getDoctorById(apt.doctorId);
      const doctorName = doctor ? doctor.name : 'Unknown Doctor';
      
      return `| ${apt.id} | ${formattedDate} | ${apt.time} | ${doctorName} | ${apt.patientName} | ${apt.reason} |`;
    });
    
    const header = `| ID | Date | Time | Doctor | Patient | Reason |\n| -- | ---- | ---- | ------ | ------- | ------ |`;
    return `${header}\n${rows.join('\n')}`;
  }

  // Get all doctors
  public getAllDoctors(): Doctor[] {
    return this.doctors.map(({ id, name, specialty }) => ({ id, name, specialty }));
  }

  // Get doctor by ID
  public getDoctorById(doctorId: string): Doctor | undefined {
    return this.doctors.find(doc => doc.id === doctorId);
  }

  // Get doctors by specialty
  public getDoctorsBySpecialty(specialty: string): Doctor[] {
    return this.doctors.filter(doc => 
      doc.specialty.toLowerCase() === specialty.toLowerCase()
    ).map(({ id, name, specialty }) => ({ id, name, specialty }));
  }

  // Get doctor availability
  public getDoctorAvailability(doctorId: string, startDate?: string, endDate?: string): { 
    doctorId: string; 
    doctorName: string; 
    specialty: string; 
    availability: AvailabilitySlot[] 
  } | null {
    const doctor = this.getDoctorById(doctorId);
    if (!doctor || !doctor.availability) return null;

    // Filter availability by date range if provided
    let availability = doctor.availability;
    if (startDate && endDate) {
      availability = availability.filter(slot => {
        return slot.date >= startDate && slot.date <= endDate;
      });
    }

    return {
      doctorId: doctor.id,
      doctorName: doctor.name,
      specialty: doctor.specialty,
      availability
    };
  }

  // Get all appointments for a specific doctor
  public getDoctorAppointments(doctorId: string): Appointment[] {
    return this.appointments.filter(apt => apt.doctorId === doctorId);
  }

  // Get all appointments for a specific patient
  public getPatientAppointments(patientName: string): Appointment[] {
    return this.appointments.filter(apt => 
      apt.patientName.toLowerCase().includes(patientName.toLowerCase())
    );
  }

  // Create a new appointment
  public createAppointment(doctorId: string, patientName: string, date: string, time: string, reason: string): AppointmentResult {
    // Check if doctor exists
    const doctor = this.getDoctorById(doctorId);
    if (!doctor) return { success: false, error: "Doctor not found" };

    // Check if the requested time slot is available
    const availabilitySlot = doctor.availability?.find(slot => slot.date === date);
    if (!availabilitySlot || !availabilitySlot.times.includes(time)) {
      return { success: false, error: "Selected time slot is not available" };
    }

    // Check if there's already an appointment at this time
    const conflictingAppointment = this.appointments.find(apt => 
      apt.doctorId === doctorId && apt.date === date && apt.time === time
    );
    if (conflictingAppointment) {
      return { success: false, error: "There is already an appointment at this time" };
    }

    // Create a new appointment
    const newAppointment: Appointment = {
      id: `apt${this.appointments.length + 1}`,
      doctorId,
      patientName,
      date,
      time,
      reason
    };

    // Add to appointments
    this.appointments.push(newAppointment);

    // Remove the time slot from availability
    if (doctor.availability) {
      const availabilityIndex = doctor.availability.findIndex(slot => slot.date === date);
      if (availabilityIndex !== -1) {
        const timeIndex = doctor.availability[availabilityIndex].times.indexOf(time);
        if (timeIndex !== -1) {
          doctor.availability[availabilityIndex].times.splice(timeIndex, 1);
          
          // If no more times available for this date, remove the entire date entry
          if (doctor.availability[availabilityIndex].times.length === 0) {
            doctor.availability.splice(availabilityIndex, 1);
          }
        }
      }
    }

    return { success: true, appointment: newAppointment };
  }

  // Cancel an appointment by ID
  public cancelAppointment(appointmentId: string): AppointmentResult {
    const appointmentIndex = this.appointments.findIndex(apt => apt.id === appointmentId);
    if (appointmentIndex === -1) {
      return { success: false, error: "Appointment not found" };
    }

    const appointment = this.appointments[appointmentIndex];
    
    // Remove appointment from the list
    this.appointments.splice(appointmentIndex, 1);

    // Add the time slot back to doctor's availability
    const doctor = this.getDoctorById(appointment.doctorId);
    if (doctor && doctor.availability) {
      // Find if the date already exists in availability
      const availabilitySlot = doctor.availability.find(slot => slot.date === appointment.date);
      
      if (availabilitySlot) {
        // Date exists, just add the time back (in order)
        const times = [...availabilitySlot.times, appointment.time].sort();
        availabilitySlot.times = times;
      } else {
        // Date doesn't exist in availability, add a new entry
        doctor.availability.push({
          date: appointment.date,
          times: [appointment.time]
        });
        
        // Sort availability by date
        doctor.availability.sort((a, b) => a.date.localeCompare(b.date));
      }
    }

    return { 
      success: true, 
      message: "Appointment cancelled successfully" 
    };
  }
}

// Export singleton instance
export const appointmentService = AppointmentService.getInstance();