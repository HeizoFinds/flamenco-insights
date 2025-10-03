<template>
  <div class="dashboard">
    <h1 class="page-title">{{ $t('dashboard.title') }}</h1>

    <el-row :gutter="24">
      
      <el-col :xs="24" :sm="24" :md="8" :lg="8">
        
        <el-card class="box-card worker-summary-card" style="margin-bottom: 24px;">
          <template #header>
            <div class="card-header"><span>{{ $t('dashboard.workerSummary.title') }}</span></div>
          </template>
          <div v-if="loadingWorkers" class="summary-loading"><el-skeleton :rows="2" animated /></div>
          <div v-else>
            <div class="progress-bar">
              <div class="progress-segment online" :style="{ width: workerPercentages.online + '%' }" :title="$t('dashboard.workerSummary.online')"></div>
              <div class="progress-segment offline" :style="{ width: workerPercentages.offline + '%' }" :title="$t('dashboard.workerSummary.offline')"></div>
            </div>
            <div class="legend">
              <div class="legend-item">
                <span class="legend-dot online"></span>
                <span>{{ $t('dashboard.workerSummary.online') }}: <strong>{{ workerSummary.online }}</strong> ({{ workerPercentages.online.toFixed(1) }}%)</span>
              </div>
              <div class="legend-item">
                <span class="legend-dot offline"></span>
                <span>{{ $t('dashboard.workerSummary.offline') }}: <strong>{{ workerSummary.offline }}</strong> ({{ workerPercentages.offline.toFixed(1) }}%)</span>
              </div>
            </div>
          </div>
        </el-card>

        <el-card class="box-card job-queue-card">
          <template #header>
            <div class="card-header"><span>{{ $t('dashboard.jobQueue.title') }}</span></div>
          </template>
          <el-skeleton :rows="4" animated v-if="loadingJobsProgress" />
          <div v-else-if="activeJobs.length === 0" class="empty-queue">{{ $t('dashboard.jobQueue.empty') }}</div>
          <div v-else class="queue-list">
            <div v-for="job in activeJobs" :key="job.id" class="queue-item">
              <span class="job-name" :title="job.name">{{ job.name }}</span>
              <el-progress 
                type="circle" 
                :percentage="getJobProgress(job)" 
                :width="50" 
                :stroke-width="5"
                :color="progressColor(job.status)"
              />
            </div>
          </div>
        </el-card>

      </el-col>
      
      <el-col :xs="24" :sm="24" :md="16" :lg="16">
        
        <el-card class="box-card worker-list-card" style="height: 100%;">
          <template #header>
            <div class="card-header">
              <span>{{ $t('dashboard.workerList.title') }}</span>
              <div class="worker-controls">
                <el-dropdown @command="handleWorkerBatchCommand" trigger="click">
                  <el-button type="primary" size="small" :disabled="selectedWorkers.length === 0">
                    {{ $t('dashboard.workerList.batchActions') }} <el-icon class="el-icon--right"><arrow-down /></el-icon>
                  </el-button>
                  <template #dropdown>
                    <el-dropdown-menu>
                      <el-dropdown-item command="wake_up">{{ $t('dashboard.workerList.actions.wakeUp') }}</el-dropdown-item>
                      <el-dropdown-item command="sleep_after_task" divided>{{ $t('dashboard.workerList.actions.sleepAfterTask') }}</el-dropdown-item>
                      <el-dropdown-item command="sleep_immediately">{{ $t('dashboard.workerList.actions.sleepImmediately') }}</el-dropdown-item>
                      <el-dropdown-item command="shutdown_after_task" divided>{{ $t('dashboard.workerList.actions.shutdownAfterTask') }}</el-dropdown-item>
                      <el-dropdown-item command="shutdown_immediately">{{ $t('dashboard.workerList.actions.shutdownImmediately') }}</el-dropdown-item>
                      <el-dropdown-item command="remove" divided class="danger-command">{{ $t('dashboard.workerList.actions.remove') }}</el-dropdown-item>
                    </el-dropdown-menu>
                  </template>
                </el-dropdown>
                <el-radio-group v-model="workerViewMode" size="small" style="margin-left: 16px;">
                  <el-radio-button label="page">{{ $t('dashboard.workerList.viewMode.page') }}</el-radio-button>
                  <el-radio-button label="scroll">{{ $t('dashboard.workerList.viewMode.scroll') }}</el-radio-button>
                </el-radio-group>
              </div>
            </div>
          </template>
          <el-skeleton :rows="5" animated v-if="loadingWorkers" />
          <el-table
            :data="paginatedWorkers"
            :height="workerViewMode === 'scroll' ? 400 : undefined"
            style="width: 100%"
            @selection-change="handleSelectionChange"
            @row-click="showWorkerDetails"
            :row-style="{ cursor: 'pointer' }"
            v-else
          >
            <el-table-column type="selection" width="45" />
            <el-table-column :label="$t('dashboard.workerList.columns.status')" width="120">
              <template #default="scope">
                <div style="display: flex; align-items: center;">
                  <el-tag :type="workerStatusTag(scope.row.status)" size="small" effect="light">{{ scope.row.status }}</el-tag>
                  <el-tooltip
                    v-if="scope.row.status.endsWith('-after-task')"
                    effect="dark"
                    :content="scope.row.status === 'sleeping-after-task' ? $t('dashboard.workerList.tooltips.sleepAfterTask') : $t('dashboard.workerList.tooltips.shutdownAfterTask')"
                    placement="top"
                  >
                    <el-icon style="margin-left: 8px; color: #E6A23C;"><Timer /></el-icon>
                  </el-tooltip>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="name" :label="$t('dashboard.workerList.columns.name')" show-overflow-tooltip />
            <el-table-column :label="$t('dashboard.workerList.columns.notes')" min-width="150" show-overflow-tooltip>
              <template #default="scope">
                <div class="note-cell">
                  <span>{{ workerNotes[scope.row.id] || '...' }}</span>
                  <el-button 
                    :icon="EditPen" 
                    text 
                    circle 
                    @click.stop="openNoteDialog(scope.row)" 
                  />
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="version" :label="$t('dashboard.workerList.columns.version')" width="80" />
            <el-table-column :label="$t('dashboard.workerList.columns.plan')" width="60" align="center">
              <template #default="scope">
                <el-tooltip
                  v-if="plannedActions[scope.row.id] === 'sleep_after_task'"
                  effect="dark"
                  :content="$t('dashboard.workerList.tooltips.sleepAfterTask')"
                  placement="top"
                >
                  <el-icon color="#E6A23C"><Moon /></el-icon>
                </el-tooltip>
                
                <el-tooltip
                  v-if="plannedActions[scope.row.id] === 'shutdown_after_task'"
                  effect="dark"
                  :content="$t('dashboard.workerList.tooltips.shutdownAfterTask')"
                  placement="top"
                >
                  <el-icon color="#F56C6C"><SwitchButton /></el-icon>
                </el-tooltip>
              </template>
            </el-table-column>
          </el-table>
          <el-pagination
            v-if="workerViewMode === 'page' && !loadingWorkers && workers.length > 0"
            layout="prev, pager, next, ->, total"
            :total="workers.length"
            :page-size="workerPageSize"
            v-model:current-page="workerCurrentPage"
            background
            small
            style="margin-top: 15px;"
          />
        </el-card>

      </el-col>

    </el-row>

    <el-row :gutter="24" style="margin-top: 24px;">
      <el-col :span="24">
        <el-card class="box-card table-card">
          <template #header>
              <div class="card-header"><span>{{ $t('dashboard.jobList.title') }}</span></div>
          </template>
          <el-skeleton :rows="10" animated v-if="loading" />
          <el-table :data="jobs" style="width: 100%" :empty-text="$t('dashboard.jobList.empty')" v-else>
            <el-table-column prop="name" :label="$t('dashboard.jobList.columns.name')" min-width="200">
              <template #default="scope">
                  <span class="job-link" @click="handleRowClick(scope.row)">{{ scope.row.name }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="status" :label="$t('dashboard.jobList.columns.status')" width="120">
                <template #default="scope">
                    <el-tag :type="statusTagType(scope.row.status)" effect="light" size="small">
                        {{ scope.row.status }}
                    </el-tag>
                </template>
            </el-table-column>
            <el-table-column prop="priority" :label="$t('dashboard.jobList.columns.priority')" width="100" />
            <el-table-column prop="type" :label="$t('dashboard.jobList.columns.type')" width="150" />
            <el-table-column :label="$t('dashboard.jobList.columns.submitted')" width="200">
              <template #default="scope">
                <span class="time-cell">{{ new Date(scope.row.created).toLocaleString() }}</span>
              </template>
            </el-table-column>
            <el-table-column :label="$t('dashboard.jobList.columns.actions')" width="100" align="center">
                <template #default="scope">
                    <el-dropdown @command="(cmd) => handleJobCommand(cmd, scope.row)" trigger="click">
                        <el-button circle :icon="MoreFilled" />
                        <template #dropdown>
                            <el-dropdown-menu>
                              <el-dropdown-item command="details" :icon="View">{{ $t('dashboard.jobList.actions.details') }}</el-dropdown-item>
                              <el-dropdown-item v-if="scope.row.status === 'active'" command="pause" :icon="VideoPause">{{ $t('dashboard.jobList.actions.pause') }}</el-dropdown-item>
                              <el-dropdown-item v-if="scope.row.status === 'paused'" command="resume" :icon="VideoPlay">{{ $t('dashboard.jobList.actions.resume') }}</el-dropdown-item>
                              <el-dropdown-item command="requeue" :icon="Refresh">{{ $t('dashboard.jobList.actions.requeue') }}</el-dropdown-item>
                              <el-dropdown-item command="cancel" :icon="CircleClose" divided>{{ $t('dashboard.jobList.actions.cancel') }}</el-dropdown-item>
                              <el-dropdown-item command="delete" :icon="Delete" class="danger-command">{{ $t('dashboard.jobList.actions.delete') }}</el-dropdown-item>
                            </el-dropdown-menu>
                        </template>
                    </el-dropdown>
                </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <el-dialog v-model="workerDetailDialogVisible" :title="$t('dashboard.workerDetails.title')" width="60%">
        <div v-if="loadingWorkerDetails"><el-skeleton :rows="6" animated /></div>
        <el-descriptions v-else :column="2" border>
            <el-descriptions-item :label="$t('dashboard.workerDetails.id')">{{ workerDetails.id }}</el-descriptions-item>
            <el-descriptions-item :label="$t('dashboard.workerDetails.name')">{{ workerDetails.name }}</el-descriptions-item>
            <el-descriptions-item :label="$t('dashboard.workerDetails.status')">
                <el-tag :type="workerStatusTag(workerDetails.status)" size="small">{{ workerDetails.status }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item :label="$t('dashboard.workerDetails.lastSeen')">{{ new Date(workerDetails.last_seen).toLocaleString() }}</el-descriptions-item>
            <el-descriptions-item :label="$t('dashboard.workerDetails.version')">{{ workerDetails.version }}</el-descriptions-item>
            <el-descriptions-item :label="$t('dashboard.workerDetails.ipAddress')">{{ workerDetails.ip_address }}</el-descriptions-item>
            <el-descriptions-item :label="$t('dashboard.workerDetails.platform')">{{ workerDetails.platform }}</el-descriptions-item>
            <el-descriptions-item :label="$t('dashboard.workerDetails.lastTask')">{{ (workerDetails.task && workerDetails.task.name) || 'N/A' }}</el-descriptions-item>
            <el-descriptions-item :label="$t('dashboard.workerDetails.taskTypes')" :span="2">
                <el-tag v-if="workerDetails.supported_task_types && workerDetails.supported_task_types.length" v-for="tt in workerDetails.supported_task_types" :key="tt" style="margin-right: 5px;">{{ tt }}</el-tag>
                <span v-else>N/A</span>
            </el-descriptions-item>
             <el-descriptions-item :label="$t('dashboard.workerDetails.notes')" :span="2">
                 <span>{{ workerNotes[workerDetails.id] || $t('dashboard.workerDetails.noNotes') }}</span>
                 <el-button
                    :icon="EditPen"
                    text
                    circle
                    @click.stop="openNoteDialog(workerDetails)"
                    style="margin-left: 10px;"
                 />
            </el-descriptions-item>
        </el-descriptions>
        <template #footer>
            <span class="dialog-footer">
                <el-button @click="workerDetailDialogVisible = false">{{ $t('dashboard.workerDetails.close') }}</el-button>
            </span>
        </template>
    </el-dialog>
    <el-dialog v-model="noteDialogVisible" :title="$t('dashboard.noteDialog.title', { name: editingNoteWorker?.name })" width="40%">
        <el-input
            v-model="currentNoteText"
            :rows="5"
            type="textarea"
            :placeholder="$t('dashboard.noteDialog.placeholder')"
        />
        <template #footer>
            <span class="dialog-footer">
                <el-button @click="noteDialogVisible = false">{{ $t('dashboard.noteDialog.cancel') }}</el-button>
                <el-button type="primary" @click="handleSaveNote">{{ $t('dashboard.noteDialog.save') }}</el-button>
            </span>
        </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch } from 'vue';
import { useRouter } from 'vue-router';
import api from '@/services/api';
import { ElMessage, ElMessageBox } from 'element-plus';
import { Timer, ArrowDown, MoreFilled, View, VideoPause, VideoPlay, Refresh, CircleClose, Delete, EditPen, Moon, SwitchButton } from '@element-plus/icons-vue';
import { useI18n } from 'vue-i18n';

const { t } = useI18n(); 

const jobs = ref([]);
const loading = ref(true);
const jobsWithProgress = ref([]);
const loadingJobsProgress = ref(true);

const workers = ref([]);
const loadingWorkers = ref(true);
const selectedWorkers = ref([]);
const workerViewMode = ref('page');
const workerCurrentPage = ref(1);
const workerPageSize = ref(5);
const workerDetailDialogVisible = ref(false);
const workerDetails = ref({});
const loadingWorkerDetails = ref(false);
const workerNotes = ref({});
const noteDialogVisible = ref(false);
const editingNoteWorker = ref(null);
const currentNoteText = ref('');
const plannedActions = ref({});

onMounted(() => {
  const savedActions = localStorage.getItem('flamenco-planned-actions');
  if (savedActions) {
    plannedActions.value = JSON.parse(savedActions);
  }
});

watch(plannedActions, (newActions) => {
  localStorage.setItem('flamenco-planned-actions', JSON.stringify(newActions));
}, { deep: true });

const router = useRouter();

const fetchJobs = async () => {
  loading.value = true;
  try {
    const response = await api.getJobs();
    jobs.value = response.data.jobs;
  } catch (error) {
    console.error('获取任务失败:', error);
    ElMessage.error(t('dashboard.messages.loadJobsFail'));
    jobs.value = [];
  } finally {
    loading.value = false;
  }
};

const fetchWorkers = async () => {
    loadingWorkers.value = true;
    try {
        const response = await api.getWorkers();
        workers.value = response.data.workers;

        if (workers.value.length > 0) {
            const onlineWorkerIds = new Set(workers.value.map(w => w.id));
            for (const workerId in plannedActions.value) {
                const worker = workers.value.find(w => w.id === workerId);
                if (!worker || worker.status === 'offline') {
                    delete plannedActions.value[workerId];
                }
            }
        }
    } catch (error) {
        console.error('获取 Workers 失败:', error);
        ElMessage.error(t('dashboard.messages.loadWorkersFail'));
        workers.value = [];
    } finally {
        loadingWorkers.value = false;
    }
}

const fetchWorkerNotes = async () => {
    try {
        const response = await api.getWorkerNotes();
        workerNotes.value = response.data || {};
    } catch (error) {
        console.error('获取 Worker 备注失败:', error);
    }
};
const fetchJobsWithProgress = async () => {
    loadingJobsProgress.value = true;
    try {
        const response = await api.getJobsWithProgress();
        jobsWithProgress.value = response.data.jobs || [];
    } catch (error) {
        console.error('获取任务进度失败:', error);
        ElMessage.error(t('dashboard.messages.loadQueueFail'));
    } finally {
        loadingJobsProgress.value = false;
    }
};

const workerSummary = computed(() => {
    const offlineStatuses = ['offline', 'error'];
    const online = workers.value.filter(w => !offlineStatuses.includes(w.status)).length;
    const total = workers.value.length;
    return {
        total: total,
        online: online,
        offline: total - online,
    };
});

const workerPercentages = computed(() => {
    const total = workerSummary.value.total;
    if (total === 0) return { online: 0, offline: 100 };
    return {
        online: (workerSummary.value.online / total) * 100,
        offline: (workerSummary.value.offline / total) * 100,
    };
});

const activeJobs = computed(() => {
    return jobsWithProgress.value.filter(job =>
        !['completed', 'cancelled'].includes(job.status)
    );
});

const paginatedWorkers = computed(() => {
    if (workerViewMode.value === 'scroll') {
        return workers.value;
    }
    const start = (workerCurrentPage.value - 1) * workerPageSize.value;
    const end = start + workerPageSize.value;
    return workers.value.slice(start, end);
});

const statusTagType = (status) => {
  const map = { completed: 'success', active: 'primary', error: 'danger', paused: 'warning', cancelled: 'info' };
  return map[status] || 'info';
};

const workerStatusTag = (status) => {
    const map = { active: 'success', offline: 'info', error: 'danger', sleeping: 'warning', 'shutting-down-immediately': 'danger', 'sleeping-after-task': 'warning', 'shutting-down-after-task': 'danger' };
    return map[status] || 'primary';
};

const getJobProgress = (job) => {
    if (!job.tasks_total) return 0;
    return Math.round((job.tasks_completed / job.tasks_total) * 100);
};

const progressColor = (status) => {
    const colorMap = { error: '#f56c6c', paused: '#e6a23c' };
    return colorMap[status] || '#409eff';
};

const handleRowClick = (row) => {
  if (row && row.id) {
    router.push({ name: 'job-details', params: { id: row.id } });
  }
};
const openNoteDialog = (worker) => {
    editingNoteWorker.value = worker;
    currentNoteText.value = workerNotes.value[worker.id] || '';
    noteDialogVisible.value = true;
};

const handleSaveNote = async () => {
    if (!editingNoteWorker.value) return;
    try {
        const workerId = editingNoteWorker.value.id;
        await api.saveWorkerNote(workerId, currentNoteText.value);
        workerNotes.value[workerId] = currentNoteText.value;
        ElMessage.success(t('dashboard.messages.noteSavedSuccess'));
        noteDialogVisible.value = false;
        if (workerDetailDialogVisible.value && workerDetails.value.id === workerId) {
            workerDetails.value.note = currentNoteText.value;
        }
    } catch (error) {
        ElMessage.error(t('dashboard.messages.noteSavedFail'));
    }
};
const handleJobCommand = async (command, job) => {
    const actions = {
        details: () => handleRowClick(job),
        delete: async () => {
            await ElMessageBox.confirm(
                t('dashboard.messages.deleteJobConfirm', { name: job.name }), 
                t('dashboard.messages.warning'), 
                {
                    confirmButtonText: t('dashboard.messages.confirmDelete'),
                    cancelButtonText: t('dashboard.messages.cancel'),
                    type: 'warning',
                }
            );
            await api.deleteJob(job.id);
            ElMessage.success(t('dashboard.messages.jobDeleted', { name: job.name }));
            fetchJobs();
            fetchJobsWithProgress();
        },
        pause: () => api.setJobStatus(job.id, 'pause'),
        resume: () => api.setJobStatus(job.id, 'resume'),
        requeue: () => api.setJobStatus(job.id, 'requeue'),
        cancel: () => api.setJobStatus(job.id, 'cancel'),
    };

    try {
        await actions[command]();
        if (command !== 'details' && command !== 'delete') {
            ElMessage.success(t('dashboard.messages.opSuccess', { command }));
            setTimeout(() => {
                fetchJobs();
                fetchJobsWithProgress();
            }, 500);
        }
    } catch (error) {
        if (error !== 'cancel') {
           ElMessage.error(t('dashboard.messages.opFail', { command, error: error.message || error }));
        }
    }
};

const handleSelectionChange = (val) => {
  selectedWorkers.value = val;
};

const handleWorkerBatchCommand = async (command) => {
    const workerIds = selectedWorkers.value.map(w => w.id);
    if (workerIds.length === 0) return;

    const plannedActionCommands = ['sleep_after_task', 'shutdown_after_task'];
    const clearActionCommands = ['wake_up', 'sleep_immediately', 'shutdown_immediately', 'remove'];

    if (plannedActionCommands.includes(command)) {
        workerIds.forEach(id => {
            plannedActions.value[id] = command;
        });
    } else if (clearActionCommands.includes(command)) {
        workerIds.forEach(id => {
            delete plannedActions.value[id];
        });
    }

    if (command === 'remove') {
        try {
            await ElMessageBox.confirm(
                t('dashboard.messages.removeWorkerConfirm', { count: workerIds.length }), 
                t('dashboard.messages.warning'), 
                { type: 'warning' }
            );
        } catch {
            return;
        }
    }

    try {
        await api.performWorkerBatchAction(workerIds, command);
        ElMessage.success(t('dashboard.messages.batchCommandSent', { count: workerIds.length, command }));
        setTimeout(fetchWorkers, 1000);
    } catch (error) {
        ElMessage.error(t('dashboard.messages.batchCommandFail', { error: error.message || error }));
    }
};

const showWorkerDetails = async (row) => {
    workerDetailDialogVisible.value = true;
    loadingWorkerDetails.value = true;
    try {
        const response = await api.getWorkerDetails(row.id);
        workerDetails.value = response.data;
    } catch (error) {
        ElMessage.error(t('dashboard.messages.loadWorkerDetailsFail'));
        workerDetails.value = {};
    } finally {
        loadingWorkerDetails.value = false;
    }
};

onMounted(() => {
    fetchJobs();
    fetchWorkers();
    fetchJobsWithProgress();
    fetchWorkerNotes();
    setInterval(() => {
        fetchWorkers();
        fetchJobsWithProgress();
    }, 15000);
});
</script>

<style scoped>
.page-title {
  font-size: 1.8rem;
  font-weight: 600;
  color: var(--font-color);
  margin-bottom: 24px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
}

.worker-controls {
  display: flex;
  align-items: center;
}

:deep(.el-table) {
  --el-table-header-bg-color: var(--background-color);
  --el-table-tr-bg-color: var(--white-color);
  --el-table-row-hover-bg-color: #f4f5f7;
}
:deep(.el-table th) {
  font-weight: 600;
  color: var(--font-color);
}
:deep(.el-table td) {
  color: var(--light-font-color);
}

.job-link {
  color: var(--primary-color);
  text-decoration: none;
  font-weight: 500;
  cursor: pointer;
}
.time-cell {
    font-family: 'Menlo', 'Consolas', monospace;
    font-size: 0.9em;
}

.danger-command {
    color: var(--danger-color);
}
.danger-command:hover {
    background-color: #fee;
    color: var(--danger-color);
}

.worker-summary-card .progress-bar {
  display: flex;
  width: 100%;
  height: 12px;
  border-radius: 6px;
  overflow: hidden;
  margin-bottom: 16px;
  background-color: var(--border-color);
}
.worker-summary-card .progress-segment {
  height: 100%;
  transition: width 0.3s ease;
}
.progress-segment.online { background-color: var(--success-color); }
.progress-segment.offline { background-color: var(--danger-color); }

.worker-summary-card .legend {
  font-size: 14px;
}
.worker-summary-card .legend-item {
  display: flex;
  align-items: center;
  margin-bottom: 8px;
}
.worker-summary-card .legend-item:last-child { margin-bottom: 0; }
.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  margin-right: 8px;
}
.legend-dot.online { background-color: var(--success-color); }
.legend-dot.offline { background-color: var(--danger-color); }
.legend-item span { color: var(--light-font-color); }
.legend-item strong { color: var(--font-color); }

.empty-queue {
  text-align: center;
  color: var(--light-font-color);
  padding: 20px 0;
}
.queue-list {
  max-height: 400px;
  overflow-y: auto;
}
.queue-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 4px;
  border-bottom: 1px solid var(--border-color);
}
.queue-item:last-child {
  border-bottom: none;
}
.queue-item .job-name {
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-right: 16px;
  font-size: 14px;
}
.note-cell {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.note-cell span {
  flex-grow: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--light-font-color);
}
@media (max-width: 768px) {
  .card-header {
    flex-direction: column;
    align-items: flex-start;
  }
  .worker-controls {
    margin-top: 10px;
    width: 100%;
    justify-content: space-between;
  }
  .job-queue-card {
    margin-top: 24px;
    margin-bottom: 24px;
  }
}
</style>
