import type { AnalysisSummary } from '../types/firsthome'

export function analysisSummary(summary?: AnalysisSummary | null, fallbackStatus?: string): AnalysisSummary {
  if (summary) return summary
  if (fallbackStatus === 'analyzed') {
    return {
      stage: 'verified',
      label: '분석 완료',
      tone: 'success',
      next_action: '주택형 옵션과 자금 일정을 비교할 수 있습니다.',
      is_mock: false,
      source: '',
      schema_version: '',
      extraction_status: '',
      document_status: '',
      document_count: 0,
      unit_option_count: 0,
      latest_error: '',
    }
  }
  return {
    stage: fallbackStatus || 'not_requested',
    label: fallbackStatus === 'failed' ? '분석 실패' : fallbackStatus === 'pending' ? '분석 중' : '분석 필요',
    tone: fallbackStatus === 'failed' ? 'danger' : fallbackStatus === 'pending' ? 'info' : 'muted',
    next_action: fallbackStatus === 'failed' ? '공식 PDF 발견 또는 추출 조건을 확인하세요.' : '공식 문서 discovery와 PDF 분석을 실행하세요.',
    is_mock: false,
    source: '',
    schema_version: '',
    extraction_status: '',
    document_status: '',
    document_count: 0,
    unit_option_count: 0,
    latest_error: '',
  }
}

export function analysisBadgeClass(summary?: AnalysisSummary | null) {
  const tone = summary?.tone ?? 'muted'
  if (tone === 'success') return 'bg-emerald-50 text-emerald-700'
  if (tone === 'warning') return 'bg-amber-50 text-amber-700'
  if (tone === 'danger') return 'bg-rose-50 text-rose-700'
  if (tone === 'info') return 'bg-blue-50 text-blue-700'
  return 'bg-slate-100 text-slate-700'
}
