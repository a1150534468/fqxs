import type { WizardOption } from './types';

export const wizardSteps = [
  '世界观',
  '人物',
  '地图',
  '故事线',
  '情节弧',
  '开始',
  '维度框架',
  '主要角色',
  '地图系统',
  '主线支线',
  '剧情抽离',
  '进入工作台',
];

export const WIZARD_STEP_TYPES = [
  'worldview',
  'characters',
  'map',
  'storyline',
  'plot_arc',
  'opening',
  'dimension_framework',
  'main_characters',
  'map_system',
  'main_sub_plots',
  'plot_extraction',
];

export const statusColors: Record<string, string> = {
  active: 'green',
  paused: 'orange',
  completed: 'blue',
  abandoned: 'red',
};

export const chapterStatusTag: Record<string, { color: string; label: string }> = {
  generating: { color: 'processing', label: '生成中' },
  pending_review: { color: 'warning', label: '待审核' },
  approved: { color: 'green', label: '已审核' },
  published: { color: 'blue', label: '已发布' },
  failed: { color: 'red', label: '失败' },
};

export const STEP_PRESETS: Record<string, WizardOption[]> = {
  世界观: [
    { title: '仙侠多宇宙', preview: '古典修真与多宇宙折叠,主角穿行不同宇宙协调力量。' },
    { title: '赛博朋克华夏', preview: '霓虹与符箓共存的未来都市,AI 神明统治上城。' },
    { title: '末日废土', preview: '尘海覆盖大陆,幸存者靠巨型机甲与异化植物对抗。' },
    { title: '悬疑都市', preview: '雾城永夜下雨,超感者必须解开连续失踪案的谜团。' },
  ],
  人物: [
    { title: '冷静女主角', preview: '逻辑型女主,擅长情报推演,在关键时刻保持冷静。' },
    { title: '双重身份男主', preview: '表面是音乐家,暗地是影子杀手,内心分裂矛盾。' },
    { title: '搞笑搭档', preview: '爱吐槽的副手,紧张时打破沉默,关键时刻靠谱。' },
    { title: 'AI 管家', preview: '拥有自我意识的 AI,主角唯一信任的伙伴。' },
  ],
  地图: [
    { title: '主城-云海街区', preview: '浮空城边缘,被撕裂的街区,贵族与流民壁垒森严。' },
    { title: '地下迷宫', preview: '废弃避难所改造成的迷宫,布满旧时代机枪与陷阱。' },
    { title: '天空浮岛', preview: '仅凭灵石悬空的岛屿,拥有独立生态与禁空结界。' },
    { title: '三界交汇点', preview: '现实、虚拟、副本三界交错的核心枢纽,高潮所在。' },
  ],
  故事线: [
    { title: '复仇/赎罪双线', preview: '主线追凶,支线赎罪;两线在真相处汇合爆发。' },
    { title: '成长+破案并行', preview: '每破一案触发成长节点,能力与情感同步升级。' },
    { title: '恋爱与权谋', preview: '感情线与权力博弈交织,阵营选择影响情感结局。' },
    { title: '师徒羁绊', preview: '师徒身份隐藏巨大阴谋,情感羁绊构成最终抉择。' },
  ],
  情节弧: [
    { title: '从失忆开始', preview: '开局失忆,借助 AI 记录重塑记忆,同时揭露阴谋。' },
    { title: '极限求生', preview: '在不可居住区求生,每章一个致命挑战。' },
    { title: '反派洗白', preview: '前期看似反派,逐章揭露其真实动机并完成洗白。' },
    { title: '黑化救赎', preview: '主角经历黑化高潮,最终靠伙伴拉回正轨。' },
  ],
  开始: [
    { title: '废墟中苏醒', preview: '主角在陌生废墟中醒来,身边只有一枚神秘信物。' },
    { title: '赴约遭伏击', preview: '开场赴一场关键宴席,却中途遭遇致命伏击。' },
    { title: '继承遗物', preview: '平凡少年继承神秘长辈遗物,命运就此转向。' },
    { title: '逃亡之夜', preview: '一夜之间被卷入阴谋,带着秘密连夜逃出生天。' },
  ],
  维度框架: [
    { title: '三界九层', preview: '人、灵、渊三界各分三层,跨层需突破空间法则。' },
    { title: '平行时空叠合', preview: '多个平行时空彼此渗透,事件会在镜像维度回响。' },
    { title: '现实与梦境', preview: '梦境是另一层真实世界,主角在双维度间游走。' },
    { title: '意识上载网络', preview: '肉身与数字意识并存,切换身份即切换维度。' },
  ],
  主要角色: [
    { title: '核心三人组', preview: '主角+军师+武力担当,各自背负无法言说的过往。' },
    { title: '宿敌双子', preview: '光明主角与暗面宿敌互为镜像,同源却殊途。' },
    { title: '师父与门徒', preview: '隐退大师重出江湖,唯一传人承担全部希望。' },
    { title: '失散血亲', preview: '流落各地的兄妹/姐弟,带着同一枚信物寻找彼此。' },
  ],
  地图系统: [
    { title: '城邦联邦', preview: '七座城邦组成松散联邦,各自掌控一种核心资源。' },
    { title: '大陆阶梯', preview: '大陆按海拔分四阶梯,越高越靠近禁地真相。' },
    { title: '环海群岛', preview: '星环状分布的群岛,洋流决定通行的时机与路径。' },
    { title: '地下都市网', preview: '地表荒芜,人类迁入地下都市网,靠管道列车联通。' },
  ],
  主线支线: [
    { title: '寻宝+洗冤', preview: '主线寻找传说遗宝,支线为恩人洗清冤屈。' },
    { title: '复国+修心', preview: '主线光复故国,支线修补主角破碎的道心。' },
    { title: '救人+追凶', preview: '主线解救被掳至亲,支线层层追查幕后真凶。' },
    { title: '结盟+养成', preview: '主线缔结跨势力联盟,支线培养关键下一代。' },
  ],
  剧情抽离: [
    { title: '三幕骨架', preview: '起承转合拆成三幕,每幕一次不可逆的抉择点。' },
    { title: '五节点模型', preview: '触发、成长、危机、觉醒、决战五节点串联全局。' },
    { title: '悬念链条', preview: '每章末尾丢出新悬念,形成环环相扣的推进节奏。' },
    { title: '情绪曲线', preview: '按情绪高低起伏编排章节,避免读者疲劳点堆积。' },
  ],
};

export const formatNumber = (value: number | undefined) => {
  if (!value) return 0;
  return value.toLocaleString('zh-CN');
};
