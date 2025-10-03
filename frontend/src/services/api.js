import axios from 'axios';

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_APP_BASE_API, 
  headers: {
    'Content-Type': 'application/json',
  },
});

export default {
  getJobs() {
    return apiClient.get('/jobs');
  },
  getJobsWithProgress() {
    return apiClient.get('/jobs/with-progress');
  },
  getJobDetails(jobId) {
    return apiClient.get(`/jobs/${jobId}/details`);
  },
  
  setJobStatus(jobId, statusAction) {
    return apiClient.post(`/jobs/${jobId}/status`, { status: statusAction });
  },
  deleteJob(jobId) {
    return apiClient.delete(`/jobs/${jobId}`);
  },

  getWorkers() {
    return apiClient.get('/workers');
  },
  getWorkerDetails(workerId) {
    return apiClient.get(`/workers/${workerId}`);
  },
  performWorkerBatchAction(workerIds, action) {
    return apiClient.post('/workers/batch-action', {
      worker_ids: workerIds,
      action: action,
    });
  },
   getWorkerNotes() {
    return apiClient.get('/workers/notes');
  },
  saveWorkerNote(workerId, note) {
    return apiClient.post(`/workers/${workerId}/note`, { note });
  },
};
