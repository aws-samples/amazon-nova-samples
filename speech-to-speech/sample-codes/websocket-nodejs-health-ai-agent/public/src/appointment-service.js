// appointment-service.js
// Service layer for appointment functionality
// This integrates with AppointmentDatabase.js

import appointmentDB from './AppointmentDatabase.js';
import { addAgentAction, updateAgentStatusUI } from './action-panel.js';

/**
 * Class to handle appointment-related operations
 */
class AppointmentService {
  constructor() {
    // Singleton pattern
    if (AppointmentService.instance) {
      return AppointmentService.instance;
    }
    AppointmentService.instance = this;
  }

  /**
   * Get all available doctors
   * @returns {Array} Array of doctor objects
   */
  getAllDoctors() {
    try {
      const doctors = appointmentDB.getAllDoctors();
      addAgentAction('system', 'Retrieved Doctors', `Found ${doctors.length} doctors`);
      return doctors;
    } catch (error) {
      console.error('Error getting doctors:', error);
      addAgentAction('error', 'Error Retrieving Doctors', error.message || 'Unknown error');
      return [];
    }
  }

  /**
   * Get doctor by specialty
   * @param {string} specialty Doctor specialty
   * @returns {Array} Array of doctor objects
   */
  getDoctorsBySpecialty(specialty) {
    try {
      const doctors = appointmentDB.getDoctorsBySpecialty(specialty);
      addAgentAction('system', 'Retrieved Doctors by Specialty', 
        `Found ${doctors.length} ${specialty} doctors`);
      return doctors;
    } catch (error) {
      console.error(`Error getting doctors by specialty (${specialty}):`, error);
      addAgentAction('error', 'Error Retrieving Doctors', error.message || 'Unknown error');
      return [];
    }
  }

  /**
   * Get doctor availability
   * @param {string} doctorId Doctor ID
   * @param {string} startDate Start date (YYYY-MM-DD)
   * @param {string} endDate End date (YYYY-MM-DD)
   * @returns {Object} Doctor availability object
   */
  getDoctorAvailability(doctorId, startDate = null, endDate = null) {
    try {
      const availability = appointmentDB.getDoctorAvailability(doctorId, startDate, endDate);
      
      if (!availability) {
        addAgentAction('error', 'Doctor Not Found', `No doctor found with ID: ${doctorId}`);
        return null;
      }
      
      const slotCount = availability.availability.reduce((count, day) => 
        count + day.times.length, 0);
      
      addAgentAction('system', 'Retrieved Doctor Availability', 
        `Dr. ${availability.doctorName} has ${slotCount} available time slots`);
      
      return availability;
    } catch (error) {
      console.error(`Error getting doctor availability (${doctorId}):`, error);
      addAgentAction('error', 'Error Retrieving Availability', error.message || 'Unknown error');
      return null;
    }
  }

  /**
   * Create a new appointment
   * @param {string} doctorId Doctor ID
   * @param {string} patientName Patient name
   * @param {string} date Appointment date (YYYY-MM-DD)
   * @param {string} time Appointment time (HH:MM)
   * @param {string} reason Appointment reason
   * @returns {Object} Result object with success flag and message or appointment
   */
  createAppointment(doctorId, patientName, date, time, reason) {
    try {
      updateAgentStatusUI('processing', 'Creating Appointment');
      
      const result = appointmentDB.createAppointment(
        doctorId, patientName, date, time, reason
      );
      
      if (result.success) {
        addAgentAction('system', 'Appointment Created', 
          `Appointment for ${patientName} with doctor ID ${doctorId} on ${date} at ${time}`);
      } else {
        addAgentAction('error', 'Appointment Creation Failed', result.message);
      }
      
      updateAgentStatusUI('idle', 'Idle');
      return result;
    } catch (error) {
      console.error('Error creating appointment:', error);
      addAgentAction('error', 'Error Creating Appointment', error.message || 'Unknown error');
      updateAgentStatusUI('idle', 'Idle');
      return { success: false, message: error.message || 'Unknown error occurred' };
    }
  }

  /**
   * Get patient appointments
   * @param {string} patientName Patient name
   * @returns {Array} Array of appointment objects
   */
  getPatientAppointments(patientName) {
    try {
      const appointments = appointmentDB.getPatientAppointments(patientName);
      
      addAgentAction('system', 'Retrieved Patient Appointments', 
        `Found ${appointments.length} appointments for ${patientName}`);
      
      // Enhance appointments with doctor names
      return appointments.map(apt => {
        const doctor = appointmentDB.getDoctorById(apt.doctorId);
        return {
          ...apt,
          doctorName: doctor ? doctor.name : 'Unknown Doctor'
        };
      });
    } catch (error) {
      console.error(`Error getting patient appointments (${patientName}):`, error);
      addAgentAction('error', 'Error Retrieving Appointments', error.message || 'Unknown error');
      return [];
    }
  }

  /**
   * Cancel an appointment
   * @param {string} appointmentId Appointment ID
   * @returns {Object} Result object with success flag and message
   */
  cancelAppointment(appointmentId) {
    try {
      updateAgentStatusUI('processing', 'Cancelling Appointment');
      
      const result = appointmentDB.cancelAppointment(appointmentId);
      
      if (result.success) {
        addAgentAction('system', 'Appointment Cancelled', 
          `Successfully cancelled appointment ${appointmentId}`);
      } else {
        addAgentAction('error', 'Appointment Cancellation Failed', result.message);
      }
      
      updateAgentStatusUI('idle', 'Idle');
      return result;
    } catch (error) {
      console.error(`Error cancelling appointment (${appointmentId}):`, error);
      addAgentAction('error', 'Error Cancelling Appointment', error.message || 'Unknown error');
      updateAgentStatusUI('idle', 'Idle');
      return { success: false, message: error.message || 'Unknown error occurred' };
    }
  }
}

// Export singleton instance
export default new AppointmentService();