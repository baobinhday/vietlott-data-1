export type Lang = 'vi';

const current: Lang = 'vi';

const dict: Record<string, string> = {
  // App shell
  'app.title': 'Vietlott Strategy Builder',

  // Tabs
  'tabs.pipeline': 'Pipeline',
  'tabs.generate': 'Tạo vé',
  'tabs.backtest': 'Backtest',

  // Header
  'header.help': 'Trợ giúp',
  'header.reset': 'Đặt lại',
  'header.resetConfirm': 'Đặt lại trình tạo về trống? Pipeline đã lưu sẽ bị xóa.',
  'header.theme': 'Đổi chủ đề',

  // Status
  'status.connecting': 'Đang kết nối…',
  'status.ready': 'API sẵn sàng',
  'status.offline': 'API ngoại tuyến (mặc định)',
  'status.loadFailed': 'Tải dữ liệu ban đầu thất bại',

  // Errors
  'error.startFailed': 'Khởi động thất bại',

  // Flow indicator
  'flow.label': 'Các bước',
  'flow.product': 'Sản phẩm',
  'flow.groups': 'Nhóm',
  'flow.filters': 'Bộ lọc',
  'flow.generate': 'Tạo vé / Backtest',

  // Onboarding
  'onboarding.title': 'Tạo pipeline đầu tiên',
  'onboarding.intro': 'Chọn mẫu để bắt đầu. Mỗi nhóm là một chuỗi 1+ bước: bước đầu đề xuất pool, các bước sau lọc từ pool đó. Chỉnh sửa sau được.',
  'onboarding.whatIsPipeline': 'Pipeline là gì?',
  'onboarding.bullet1': 'Pipeline chọn số từ các nhóm chiến lược.',
  'onboarding.bullet2': 'Mỗi nhóm là chuỗi bước: đề xuất pool → lọc → ...',
  'onboarding.bullet3': 'Bộ lọc sau loại vé không thỏa ràng buộc.',
  'onboarding.bullet4': 'Backtest đánh giá pipeline trên dữ liệu lịch sử.',
  'onboarding.or': 'hoặc',
  'onboarding.addManual': '+ Tự thêm nhóm',

  // Presets
  'preset.steinerTopNumbers': 'Steiner',
  'preset.steinerTopNumbers.desc': 'Chọn 6 số từ pool Steiner',
  'preset.hybridPool': 'Hybrid',
  'preset.hybridPool.desc': 'Steiner đề xuất pool, Frequency lọc từ pool đó.',
  'preset.frequencyMarkov': 'Tần suất + Markov',
  'preset.frequencyMarkov.desc': 'Số nóng + Markov',
  'preset.longAbsence': 'Số vắng lâu',
  'preset.longAbsence.desc': 'Ưu tiên số lâu chưa về',

  // Help modal
  'help.title': 'Trợ giúp',
  'help.whatIsThis': 'Đây là gì?',
  'help.whatIsThis.text': 'Kết hợp chiến lược, tạo vé và backtest.',
  'help.strategies': 'Chiến lược',
  'help.strategies.text': 'Steiner, Tần suất, Markov, Số vắng lâu, Hỗn hợp, Ngẫu nhiên.',
  'help.howTo': 'Cách dùng',
  'help.howTo.text': 'Chọn sản phẩm → dùng mẫu hoặc thêm nhóm → Tạo vé / Backtest.',
  'help.docs': 'Tài liệu',
  'help.openDocs': 'Mở helper.md',
  'help.resetEmpty': 'Đặt lại trống',

  // Pipeline builder
  'builder.product': 'Sản phẩm',
  'builder.groups': 'Nhóm',
  'builder.addGroup': '+ Thêm nhóm',
  'builder.combiner': 'Kết hợp',
  'builder.groupNamePlaceholder': 'Tên nhóm',
  'builder.dragToReorder': 'Kéo để sắp xếp',
  'builder.removeGroup': 'Xóa',
  'builder.strategy': 'Chiến lược',

  // Combiner methods
  'combiner.concatenate': 'Nối tiếp',
  'combiner.union': 'Hợp',
  'combiner.intersect': 'Giao',
  'combiner.weighted': 'Trọng số',

  // Strategy param labels
  'param.lookback_days': 'Ngày lịch sử',
  'param.strategy_type': 'Kiểu',
  'param.selection_weight': 'Trọng số chọn',
  'param.top_n': 'Top N',
  'param.avoid_weight': 'Trọng số tránh',
  'param.pattern_weight': 'Trọng số mẫu',
  'param.half_life_days': 'Ngày bán rã',
  'param.hot': 'Ưu tiên nóng',
  'param.smoothing': 'Làm mượt',
  'param.top_k': 'Top K',
  'param.coverage': 'Độ phủ',

  // Param tooltip fallback
  'param.noDescription': 'Không có mô tả.',
  'param.bounds': 'tối thiểu: {min} · tối đa: {max}',

  // Sizing fields
  'sizing.poolSize': 'Kích thước pool',
  'sizing.pickCount': 'Số lượng chọn',

  // Estimator
  'estimator.title': 'Ước tính',
  'estimator.ticketsToGenerate': 'Số vé cần tạo',
  'estimator.generate': '⚡ Tạo vé',
  'estimator.generating': '<span class="spinner"></span> Đang tạo…',
  'estimator.costLabel': '{count} vé × {price}',
  'estimator.detail': '{groups} nhóm, {picks} lượt chọn',
  'estimator.generatedTickets': 'Đã tạo {count} vé',
  'estimator.totalCost': 'Tổng: {cost}',
  'estimator.generateFailed': 'Tạo vé thất bại',

  // Backtest
  'backtest.title': 'Backtest',
  'backtest.dateFrom': 'Từ ngày',
  'backtest.dateTo': 'Đến ngày',
  'backtest.ticketsPerDraw': 'Số vé mỗi kỳ quay',
  'backtest.last7': '7 ngày qua',
  'backtest.last30': '30 ngày qua',
  'backtest.last90': '90 ngày qua',
  'backtest.last365': '1 năm qua',
  'backtest.ytd': 'Từ đầu năm',
  'backtest.ticketsPerDrawHelp': 'Số lượng vé giả định mua ở mỗi kỳ quay khi chạy backtest.',
  'backtest.run': 'Chạy backtest',
  'backtest.selectRange': 'Chọn cả ngày bắt đầu và kết thúc',
  'backtest.running': '<div class="spinner"></div><span>Đang chạy backtest…</span>',
  'backtest.empty': 'Chạy backtest để xem kết quả',
  'backtest.draws': 'Số kỳ',
  'backtest.totalCost': 'Chi phí',
  'backtest.totalRevenue': 'Doanh thu',
  'backtest.netProfit': 'Lợi nhuận',
  'backtest.roi': 'ROI',
  'backtest.bestMatch': 'Trúng nhiều nhất',
  'backtest.avgMatch': 'Trúng trung bình',
  'backtest.matchesDistribution': 'Phân bố số trúng',
  'backtest.cumulativeProfit': 'Lợi nhuận tích lũy',
  'backtest.matchLabel': '{count} trúng',
  'backtest.perDrawTitle': 'Kết quả từng kỳ',
  'backtest.prevPage': 'Trước',
  'backtest.nextPage': 'Sau',
  'backtest.pageInfo': 'Trang {page} / {total}',
  'backtest.moreTickets': '+ {n} vé khác',
  'backtest.date': 'Ngày',
  'backtest.ticket': 'Vé',
  'backtest.actual': 'Kết quả',
  'backtest.matches': 'Trúng',
  'backtest.prize': 'Giải',
  'backtest.cumProfit': 'Lũy kế',
  'backtest.failed': 'Backtest thất bại',

  // Group chain
  'group.steps': 'Chuỗi chiến lược',
  'group.step': 'Bước {n}',
  'group.addStep': '+ Thêm bước',
  'group.removeStep': 'Xóa bước',
  'group.poolSize': 'Pool size',
  'group.poolSizeAuto': '(tự động)',
  'group.poolSizeTooltip': 'Bước 1: kích thước pool ban đầu. Các bước sau: số lượng còn lại sau khi lọc. Để trống = tự động.',
  'group.pickCount': 'Chọn {n} số từ pool cuối',
  'group.pickCountHelper': '→ đóng góp {n} / {total} số cho vé',
  'group.stepTooltip': 'Bước 1 đề xuất pool, các bước sau lọc từ pool đó',
  'group.collapseParams': 'Thu gọn tham số',
  'group.expandParams': 'Mở tham số',

  // Filters
  'filters.title': 'Bộ lọc ràng buộc vé',
  'filters.min_sum': 'Tổng tối thiểu',
  'filters.max_sum': 'Tổng tối đa',
  'filters.min_even': 'Chẵn tối thiểu',
  'filters.max_even': 'Chẵn tối đa',
  'filters.min_odd': 'Lẻ tối thiểu',
  'filters.max_odd': 'Lẻ tối đa',
  'filters.any': 'Bất kỳ',
  'filter.minSum.tooltip': 'Tổng của tất cả số trong vé phải ≥ giá trị này. Phạm vi hợp lệ: từ tổng nhỏ nhất đến tổng lớn nhất có thể của sản phẩm. Ví dụ: tổng tối thiểu 100 nghĩa là vé có tổng 6 số phải ≥ 100.',
  'filter.maxSum.tooltip': 'Tổng của tất cả số trong vé phải ≤ giá trị này. Phạm vi hợp lệ: từ tổng nhỏ nhất đến tổng lớn nhất có thể của sản phẩm. Ví dụ: tổng tối đa 200 nghĩa là vé có tổng 6 số phải ≤ 200.',
  'filter.minEven.tooltip': 'Số lượng số chẵn trong vé phải ≥ giá trị này. Phạm vi: 0 đến số lượng số trong vé. Để trống = không giới hạn.',
  'filter.maxEven.tooltip': 'Số lượng số chẵn trong vé phải ≤ giá trị này. Phạm vi: 0 đến số lượng số trong vé. Để trống = không giới hạn.',
  'filter.minOdd.tooltip': 'Số lượng số lẻ trong vé phải ≥ giá trị này. Phạm vi: 0 đến số lượng số trong vé. Để trống = không giới hạn.',
  'filter.maxOdd.tooltip': 'Số lượng số lẻ trong vé phải ≤ giá trị này. Phạm vi: 0 đến số lượng số trong vé. Để trống = không giới hạn.',
};

export function t(key: string, vars?: Record<string, string | number>): string {
  let s = dict[key] ?? key;
  if (vars) {
    for (const [k, v] of Object.entries(vars)) {
      s = s.replaceAll(`{${k}}`, String(v));
    }
  }
  return s;
}

export function getLang(): Lang {
  return current;
}

export function hasKey(key: string): boolean {
  return key in dict;
}

const strategyDescVi: Record<string, string> = {
  // Param descriptions
  'Number of days to analyse for frequency': 'Số ngày phân tích tần suất',
  'hot, cold, or balanced': 'nóng, lạnh, hoặc cân bằng',
  'Weight for frequency-based selection vs random': 'Trọng số chọn theo tần suất',
  'Pool size of longest-absent numbers to sample from': 'Kích thước pool số vắng lâu',
  'Number of days to look back for recent numbers': 'Số ngày lùi lại tìm số gần đây',
  'Probability of avoiding recently drawn numbers': 'Xác suất tránh số vừa quay',
  'Rolling window (days) for spacing and range statistics': 'Cửa sổ (ngày) cho thống kê khoảng cách',
  'Fraction of ticket filled with pattern-derived numbers': 'Tỷ lệ vé lấp từ mẫu',
  'Days after which a draw\'s contribution is halved': 'Số ngày để đóng góp giảm một nửa',
  'True → prefer recently frequent; False → recently rare':
    'Bật → ưu tiên số hay về; Tắt → số hiếm',
  'Fraction of ticket filled from score-weighted pool': 'Tỷ lệ vé lấp từ pool trọng số',
  'Rolling window (days) for co-occurrence counts': 'Cửa sổ (ngày) cho đồng xuất hiện',
  'Rolling window (days) for the transition matrix': 'Cửa sổ (ngày) cho ma trận chuyển tiếp',
  'Laplace smoothing constant added to every transition count': 'Hằng số làm mượt Laplace',
  'Only use draws from this many days for pair co-occurrence': 'Số ngày dùng cho cặp đồng xuất hiện',
  'Size of the Steiner candidate number pool': 'Kích thước pool ứng viên Steiner',
  'Size of the proposer\'s candidate number pool': 'Kích thước pool ứng viên đề xuất',
  'Number of disjoint Steiner ticket candidates to generate': 'Số vé Steiner rời rạc',
};

export function tParamDescription(description: string): string {
  return strategyDescVi[description] ?? description;
}

const selectOptionVi: Record<string, string> = {
  hot: 'nóng',
  cold: 'lạnh',
  balanced: 'cân bằng',
};

export function tSelectOption(value: string): string {
  return selectOptionVi[value] ?? value;
}
