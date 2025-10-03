<template>
  <div class="job-detail" v-loading="loading">

    <div class="job-header">
      <div class="job-title">
        <el-page-header @back="goBack" :content="jobInfo.name || t('jobDetail.title')" />
        <el-tag v-if="jobInfo.status" :type="statusTagType(jobInfo.status)" size="large" effect="light" round>
          {{ jobInfo.status }}
        </el-tag>
      </div>
      <div class="job-timestamps">
        <span><strong>{{ t('jobDetail.submittedAt') }}:</strong> {{ jobInfo.created ? new Date(jobInfo.created).toLocaleString() : 'N/A' }}</span>
        <span><strong>{{ t('jobDetail.lastUpdatedAt') }}:</strong> {{ jobInfo.updated ? new Date(jobInfo.updated).toLocaleString() : 'N/A' }}</span>
      </div>
    </div>

    <el-row :gutter="24" class="summary-cards">
       <el-col :xs="12" :sm="12" :md="6" :lg="6">
         <div class="info-item">
            <span class="info-item-label">{{ t('jobDetail.summary.totalSteps') }}</span>
            <p class="info-item-value">{{ animatedTotal.displayValue }}</p>
         </div>
       </el-col>
       <el-col :xs="12" :sm="12" :md="6" :lg="6">
         <div class="info-item">
            <span class="info-item-label">{{ t('jobDetail.summary.completed') }}</span>
            <p class="info-item-value success-text">{{ animatedCompleted.displayValue }}</p>
         </div>
       </el-col>
       <el-col :xs="12" :sm="12" :md="6" :lg="6">
         <div class="info-item">
            <span class="info-item-label">{{ t('jobDetail.summary.rendering') }}</span>
            <p class="info-item-value primary-text">{{ animatedRendering.displayValue }}</p>
         </div>
       </el-col>
       <el-col :xs="12" :sm="12" :md="6" :lg="6">
         <div class="info-item">
            <span class="info-item-label">{{ t('jobDetail.summary.failed') }}</span>
            <p class="info-item-value danger-text">{{ animatedFailed.displayValue }}</p>
         </div>
       </el-col>
    </el-row>

    <el-row :gutter="24" style="margin-top: 24px;">
      <el-col :xs="24" :sm="24" :md="12" :lg="12">
        <el-card class="box-card">
          <template #header><span>{{ t('jobDetail.workerContribution.title') }}</span></template>
          <div ref="pieChart" style="width: 100%; height: 400px;"></div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="24" :md="12" :lg="12">
        <el-card class="box-card">
          <template #header><span>{{ t('jobDetail.contributionDetails.title') }}</span></template>
          <el-table :data="pieChartData" style="width: 100%" height="400">
            <el-table-column prop="name" :label="t('jobDetail.contributionDetails.workerName')" />
            <el-table-column prop="value" :label="t('jobDetail.contributionDetails.framesRendered')" />
            <el-table-column :label="t('jobDetail.contributionDetails.notes')" min-width="150" show-overflow-tooltip>
              <template #default="scope">
                <div class="note-cell">
                  <span>{{ getNoteByWorkerName(scope.row.name) || '...' }}</span>
                  <el-button 
                    :icon="EditPen" 
                    text 
                    circle 
                    @click.stop="openNoteDialog(scope.row)" 
                  />
                </div>
              </template>
            </el-table-column>
            <el-table-column :label="t('jobDetail.contributionDetails.percentage')">
              <template #default="scope">
                <span v-if="tasksSummary.completed > 0">
                  {{ ((scope.row.value / tasksSummary.completed) * 100).toFixed(2) }}%
                </span>
                <span v-else>N/A</span>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <el-card class="box-card" style="margin-top: 24px;">
      <template #header><span>{{ t('jobDetail.frameTimeAnalysis.title') }}</span></template>
      <div ref="lineChart" style="width: 100%; height: 400px;"></div>
    </el-card>

    <el-card class="box-card" style="margin-top: 24px;">
      <template #header><span>{{ t('jobDetail.parameters.title') }}</span></template>
      <el-descriptions v-if="jobInfo.settings" :column="2" border>
        <el-descriptions-item :label="t('jobDetail.parameters.frameRange')">{{ jobInfo.settings.frames }}</el-descriptions-item>
        <el-descriptions-item :label="t('jobDetail.parameters.format')">{{ jobInfo.settings.format }}</el-descriptions-item>
        <el-descriptions-item :label="t('jobDetail.parameters.scene')">{{ jobInfo.settings.scene }}</el-descriptions-item>
        <el-descriptions-item :label="t('jobDetail.parameters.fps')">{{ jobInfo.settings.fps }}</el-descriptions-item>
        <el-descriptions-item :label="t('jobDetail.parameters.blendFile')" :span="2">{{ jobInfo.settings.blendfile }}</el-descriptions-item>
        <el-descriptions-item :label="t('jobDetail.parameters.outputPath')" :span="2">{{ jobInfo.settings.render_output_path }}</el-descriptions-item>
        <el-descriptions-item :label="t('jobDetail.parameters.taskType')">{{ jobInfo.type }}</el-descriptions-item>
        <el-descriptions-item :label="t('jobDetail.parameters.taskId')">{{ jobInfo.id }}</el-descriptions-item>
      </el-descriptions>
       <div v-else class="no-data-small">{{ t('jobDetail.parameters.noData') }}</div>
    </el-card>
    
    <el-dialog v-model="noteDialogVisible" :title="t('dashboard.noteDialog.title', { name: editingNoteWorker?.name })" width="40%">
        <el-input
            v-model="currentNoteText"
            :rows="5"
            type="textarea"
            :placeholder="t('dashboard.noteDialog.placeholder')"
        />
        <template #footer>
            <span class="dialog-footer">
                <el-button @click="noteDialogVisible = false">{{ t('dashboard.noteDialog.cancel') }}</el-button>
                <el-button type="primary" @click="handleSaveNote">{{ t('dashboard.noteDialog.save') }}</el-button>
            </span>
        </template>
    </el-dialog>

  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import api from '@/services/api';
import { ElMessage } from 'element-plus';
import * as echarts from 'echarts';
import { useAnimateNumber } from '@/composables/useAnimateNumber.js';
import { EditPen } from '@element-plus/icons-vue';

const { t } = useI18n();
const route = useRoute();
const router = useRouter();
const loading = ref(true);
const jobInfo = ref({});
const tasksSummary = ref({ total: 0, completed: 0, rendering: 0, failed: 0 });
const pieChartData = ref([]);
const frameTimesData = ref([]);
const pieChart = ref(null);
const lineChart = ref(null);
const jobId = route.params.id;
let pieChartInstance = null;
let lineChartInstance = null;
let pollingInterval = null;

const workers = ref([]);
const workerNotes = ref({});
const noteDialogVisible = ref(false);
const editingNoteWorker = ref(null);
const currentNoteText = ref('');

const animatedTotal = useAnimateNumber(() => tasksSummary.value.total);
const animatedCompleted = useAnimateNumber(() => tasksSummary.value.completed);
const animatedRendering = useAnimateNumber(() => tasksSummary.value.rendering);
const animatedFailed = useAnimateNumber(() => tasksSummary.value.failed);

const goBack = () => router.push('/');
const fetchJobDetails = async (isPolling = false) => {
  if (!isPolling) {
    loading.value = true;
  }
  try {
    const response = await api.getJobDetails(jobId);
    jobInfo.value = response.data.job_info || {}; 
    tasksSummary.value = response.data.tasks_summary || { total: 0, completed: 0, rendering: 0, failed: 0 };
    pieChartData.value = response.data.pie_chart_data || [];
    frameTimesData.value = response.data.frame_times || [];
  } catch (error) {
    if (!isPolling) {
      ElMessage.error(`${t('jobDetail.messages.loadError')}: ${error}`);
    }
    console.error("加载任务详情数据失败:", error);
  } finally {
    if (!isPolling) {
      loading.value = false;
    }
  }
};

const fetchWorkers = async () => {
    try {
        const response = await api.getWorkers();
        workers.value = response.data.workers;
    } catch (error) {
        console.error('获取 Workers 失败:', error);
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

const getNoteByWorkerName = (name) => {
  const worker = workers.value.find(w => w.name === name);
  return worker ? workerNotes.value[worker.id] : '';
};

const openNoteDialog = (workerData) => {
    const worker = workers.value.find(w => w.name === workerData.name);
    if (!worker) {
        ElMessage.warning(t('jobDetail.messages.workerNotFound'));
        return;
    }
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
    } catch (error) {
        ElMessage.error(t('dashboard.messages.noteSavedFail'));
    }
};

watch([pieChart, pieChartData], ([pieChartEl, data]) => {
  if (pieChartEl && data.length > 0) {
    pieChartInstance?.dispose();
    pieChartInstance = echarts.init(pieChartEl);
    pieChartInstance.setOption({
      backgroundColor: 'transparent',
      tooltip: { trigger: 'item', formatter: `{b}<br/>${t('jobDetail.workerContribution.tooltip')}: {c} ({d}%)` },
      legend: { orient: 'vertical', left: 'left', top: 'center', textStyle: { color: 'var(--light-font-color)' } },
      series: [{
        name: 'Worker Contribution',
        type: 'pie',
        radius: ['40%', '60%'],
        center: ['65%', '50%'],
        avoidLabelOverlap: false,
        itemStyle: { borderRadius: 10, borderColor: 'var(--white-color)', borderWidth: 4 },
        label: { show: false },
        emphasis: { label: { show: false } },
        data: data,
        color: ['#0052cc', '#ffae00', '#52c41a', '#f5222d', '#73code', '#3ba272', '#fc8452'],
      }]
    });
  } else if (pieChartEl) {
    pieChartEl.innerHTML = `<div class="no-data">${t('jobDetail.workerContribution.noData')}</div>`;
  }
});

watch([lineChart, frameTimesData], ([lineChartEl, data]) => {
    if (lineChartEl && data.length > 0) {
        lineChartInstance?.dispose();
        lineChartInstance = echarts.init(lineChartEl);
        lineChartInstance.setOption({
            backgroundColor: 'transparent',
            tooltip: { 
                trigger: 'axis', 
                formatter: (params) => {
                    const dataPoint = data[params[0].dataIndex];
                    if (!dataPoint) return t('jobDetail.frameTimeAnalysis.tooltip.loading');
                    return `<b>${t('jobDetail.frameTimeAnalysis.tooltip.frame')}:</b> ${dataPoint.frame}<br/><b>${t('jobDetail.frameTimeAnalysis.tooltip.time')}:</b> ${dataPoint.time} 秒<br/><b>${t('jobDetail.frameTimeAnalysis.tooltip.worker')}:</b> ${dataPoint.worker}`;
                }
            },
            xAxis: { type: 'category', name: t('jobDetail.frameTimeAnalysis.xAxis'), data: data.map(d => d.frame), axisLine: { lineStyle: { color: 'var(--border-color)' } }, axisLabel: { color: 'var(--light-font-color)'} },
            yAxis: { type: 'value', name: t('jobDetail.frameTimeAnalysis.yAxis'), axisLine: { lineStyle: { color: 'var(--border-color)' } }, splitLine: { lineStyle: { color: 'var(--border-color)', type: 'dashed' } }, axisLabel: { color: 'var(--light-font-color)'} },
            dataZoom: [{ bottom: 10 }, { type: 'inside' }],
            series: [{
                name: t('jobDetail.frameTimeAnalysis.tooltip.time'),
                type: 'line',
                smooth: 0.6,
                symbol: 'none',
                data: data.map(d => d.time),
                areaStyle: {
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{'offset': 0, color: 'rgba(0, 82, 204, 0.4)'}, {'offset': 1, color: 'rgba(0, 82, 204, 0.05)'}])
                },
                lineStyle: { color: 'var(--primary-color)', width: 3 },
                itemStyle: { color: 'var(--primary-color)' }
            }],
            grid: { left: '3%', right: '4%', bottom: '15%', containLabel: true },
        });
    } else if (lineChartEl) {
        lineChartEl.innerHTML = `<div class="no-data">${t('jobDetail.frameTimeAnalysis.noData')}</div>`;
    }
});


const resizeCharts = () => {
    pieChartInstance?.resize();
    lineChartInstance?.resize();
};

onMounted(() => {
    fetchJobDetails(false);
    fetchWorkers();
    fetchWorkerNotes();
    window.addEventListener('resize', resizeCharts);
    pollingInterval = setInterval(() => {
        fetchJobDetails(true);
    }, 10000);
});

onBeforeUnmount(() => {
    window.removeEventListener('resize', resizeCharts);
    pieChartInstance?.dispose();
    lineChartInstance?.dispose();
    if (pollingInterval) {
        clearInterval(pollingInterval);
    }
});

const statusTagType = (status) => {
  if (status === 'completed') return 'success';
  if (status === 'active') return 'primary';
  if (status === 'error') return 'danger';
  return 'info';
};
</script>

<style scoped>
.job-header {
  margin-bottom: 24px;
}
.job-title {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 8px;
}
:deep(.el-page-header__content) {
    color: var(--font-color);
    font-size: 22px;
    font-weight: 600;
}
.job-timestamps span {
  font-size: 14px;
  color: var(--light-font-color);
  margin-right: 20px;
}

.info-item {
    background-color: var(--white-color);
    padding: 20px;
    border-radius: 8px;
    border: 1px solid var(--border-color);
    box-shadow: 0 1px 3px var(--shadow-color);
    transition: all var(--transition-speed) ease;
    text-align: left;
}
.info-item:hover {
    transform: translateY(-4px);
    box-shadow: 0 5px 15px var(--shadow-color);
}
.info-item-label {
    color: var(--light-font-color);
    font-size: 14px;
    margin-bottom: 8px;
    display: block;
}
.info-item-value {
    font-weight: 600;
    font-size: 2em;
    color: var(--font-color);
    line-height: 1.2;
}

.primary-text { color: var(--primary-color); }
.success-text { color: var(--success-color); }
.danger-text { color: var(--danger-color); }

.no-data, .no-data-small {
  display: flex;
  justify-content: center;
  align-items: center;
  color: var(--light-font-color);
  font-size: 1.1em;
  background-color: #fcfcfc;
  border-radius: 4px;
}
.no-data {
    height: 400px;
}
.no-data-small {
    height: 100px;
    font-size: 1em;
}

.note-cell {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.note-cell span {
  flex-grow: 1;
  white-space: pre-wrap;
  overflow-wrap: break-word;
  color: var(--light-font-color);
}

:deep(.el-descriptions) {
  --el-fill-color-lighter: #fafafa;
  --el-border-color: var(--border-color);
}
:deep(.el-table) {
  --el-table-header-bg-color: var(--background-color);
}

@media (max-width: 992px) { /* Corresponds to md breakpoint */
  .el-col-sm-24 {
    margin-bottom: 24px;
  }
  .el-col-sm-24:last-child {
    margin-bottom: 0;
  }
}
@media (max-width: 768px) { /* Corresponds to xs breakpoint */
  .summary-cards .el-col {
    margin-bottom: 24px;
  }
  .summary-cards .el-col:last-child,
  .summary-cards .el-col:nth-last-child(2) {
      margin-bottom: 0;
  }
}
</style>

