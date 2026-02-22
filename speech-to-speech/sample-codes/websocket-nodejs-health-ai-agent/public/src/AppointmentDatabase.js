// src/AppointmentDatabase.js
// A simple in-memory database for doctors and appointments

class AppointmentDatabase {
  constructor() {
    // Initialize with dummy data
    this.doctors = [
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

    this.appointments = [
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
  }

  // Get all doctors
  getAllDoctors() {
    return this.doctors.map(({ id, name, specialty }) => ({ id, name, specialty }));
  }

  // Get doctor by ID
  getDoctorById(doctorId) {
    return this.doctors.find(doc => doc.id === doctorId);
  }

  // Get doctors by specialty
  getDoctorsBySpecialty(specialty) {
    return this.doctors.filter(doc => 
      doc.specialty.toLowerCase() === specialty.toLowerCase()
    ).map(({ id, name, specialty }) => ({ id, name, specialty }));
  }

  // Get doctor availability
  getDoctorAvailability(doctorId, startDate, endDate) {
    const doctor = this.getDoctorById(doctorId);
    if (!doctor) return null;

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
  getDoctorAppointments(doctorId) {
    return this.appointments.filter(apt => apt.doctorId === doctorId);
  }

  // Get all appointments for a specific patient
  getPatientAppointments(patientName) {
    return this.appointments.filter(apt => 
      apt.patientName.toLowerCase().includes(patientName.toLowerCase())
    );
  }

  // Create a new appointment
  createAppointment(doctorId, patientName, date, time, reason) {
    // Check if doctor exists
    const doctor = this.getDoctorById(doctorId);
    if (!doctor) return { success: false, message: "Doctor not found" };

    // Check if the requested time slot is available
    const availabilitySlot = doctor.availability.find(slot => slot.date === date);
    if (!availabilitySlot || !availabilitySlot.times.includes(time)) {
      return { success: false, message: "Selected time slot is not available" };
    }

    // Check if there's already an appointment at this time
    const conflictingAppointment = this.appointments.find(apt => 
      apt.doctorId === doctorId && apt.date === date && apt.time === time
    );
    if (conflictingAppointment) {
      return { success: false, message: "There is already an appointment at this time" };
    }

    // Create a new appointment
    const newAppointment = {
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
    const availabilityIndex = doctor.availability.findIndex(slot => slot.date === date);
    const timeIndex = doctor.availability[availabilityIndex].times.indexOf(time);
    doctor.availability[availabilityIndex].times.splice(timeIndex, 1);

    // If no more times available for this date, remove the entire date entry
    if (doctor.availability[availabilityIndex].times.length === 0) {
      doctor.availability.splice(availabilityIndex, 1);
    }

    return { success: true, appointment: newAppointment };
  }

  // Cancel an appointment by ID
  cancelAppointment(appointmentId) {
    const appointmentIndex = this.appointments.findIndex(apt => apt.id === appointmentId);
    if (appointmentIndex === -1) {
      return { success: false, message: "Appointment not found" };
    }

    const appointment = this.appointments[appointmentIndex];
    
    // Remove appointment from the list
    this.appointments.splice(appointmentIndex, 1);

    // Add the time slot back to doctor's availability
    const doctor = this.getDoctorById(appointment.doctorId);
    
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

    return { success: true, message: "Appointment cancelled successfully" };
  }
}

// Export singleton instance
const appointmentDB = new AppointmentDatabase();
export default appointmentDB;