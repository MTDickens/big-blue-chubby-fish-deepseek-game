// Everything the gallery can show. Positions are in three.js space (x right, y up, z toward the viewer).
export const CHARACTERS = [
  {
    id: 'bluefish', name: '蓝色大肥鱼', role: '主角', from: 'EP1 · EP2 · EP3', height: 0.9,
    blurb: '鲸鱼女仆，最爱干饭。抢过电饭煲，潜入过豆包帮总部，还从游艇上救回了大圆鲸。',
    files: ['assets/characters/bluefish.glb'],
    anims: [['idle', '待机'], ['walk', '走路'], ['run', '跑步'], ['cheer', '欢呼'], ['sign', '举点赞牌'], ['carry', '抱电饭煲'], ['swim', '游泳'], ['peek', '探头']],
    expr: {
      default: ['expr_eyes_open', 'expr_mouth_open'], cheer: ['expr_eyes_happy', 'expr_mouth_open'], carry: ['expr_eyes_happy', 'expr_mouth_cat'],
      swim: ['expr_eyes_open', 'expr_mouth_small'], peek: ['expr_eyes_open', 'expr_mouth_round'], walk: ['expr_eyes_open', 'expr_mouth_small'],
    },
    exprSets: { eyes: ['expr_eyes_open', 'expr_eyes_happy'], mouth: ['expr_mouth_open', 'expr_mouth_small', 'expr_mouth_round', 'expr_mouth_cat'] },
    props: {
      sign: { file: 'assets/characters/sign.glb', bone: 'prop', pos: [0, 0.402, 0.175] },
      carry: { file: 'assets/characters/rice_cooker.glb', bone: 'prop', pos: [0, 0.268, 0.14] },
    },
  },
  {
    id: 'babies', name: '小鲸鱼宝宝', role: '沙滩上的一群', from: 'EP1 · EP2 片尾', height: 0.25,
    blurb: '住在鲸鱼沙滩的小鲸鱼们，三种体型，喜欢蹦蹦跳跳。',
    files: ['assets/characters/whale_baby_b.glb', 'assets/characters/whale_baby_a.glb', 'assets/characters/whale_baby_c.glb'],
    anims: [['idle', '待机'], ['hop', '蹦跳'], ['flap', '拍鳍'], ['spin', '开心转圈']],
  },
  {
    id: 'whale_big', name: '大圆鲸', role: '被抓走的用户', from: 'EP3', height: 0.66,
    blurb: '圆滚滚的毛绒鲸鱼。被白色龙娘绑上游艇，最后被大肥鱼救了出来。',
    files: ['assets/characters/whale_big.glb'],
    anims: [['idle', '待机'], ['happy', '开心'], ['hop', '蹦跳'], ['struggle', '被绑挣扎']],
    expr: { default: ['expr_eyes_open', 'expr_mouth_open'], happy: ['expr_eyes_happy', 'expr_mouth_open'], struggle: ['expr_eyes_open', 'expr_mouth_small'] },
    exprSets: { eyes: ['expr_eyes_open', 'expr_eyes_happy'], mouth: ['expr_mouth_open', 'expr_mouth_small'] },
    props: { struggle: { file: 'assets/characters/rope.glb', bone: 'body', pos: [0, 0, 0] } },
  },
  {
    id: 'dragon', name: '白色龙娘', role: 'EP3 对手', from: 'EP3', height: 1.12,
    blurb: '住在豪华游艇上的白色龙娘，龙角、龙翼和一条长长的龙尾。',
    files: ['assets/characters/dragon.glb'],
    anims: [['idle', '待机'], ['walk', '走路'], ['flap', '扇翅膀'], ['point', '指人']],
    expr: { default: ['expr_eyes_open', 'expr_mouth_small'], point: ['expr_eyes_open', 'expr_mouth_open'] },
    exprSets: { eyes: ['expr_eyes_open', 'expr_eyes_happy'], mouth: ['expr_mouth_small', 'expr_mouth_open'] },
  },
  {
    id: 'doubao', name: '豆包帮首领', role: 'EP2 Boss', from: 'EP2', height: 1.2,
    blurb: '豆包帮的老大，守着黄金电饭煲。被大肥鱼一招放倒。',
    files: ['assets/characters/doubao.glb'],
    anims: [['idle', '待机'], ['walk', '走路'], ['stomp', '生气跺脚'], ['knocked', '被放倒']],
    once: ['knocked'],
    expr: { default: ['expr_eyes_open', 'expr_mouth_small'], stomp: ['expr_eyes_open', 'expr_mouth_round'], knocked: ['expr_eyes_open', 'expr_mouth_round'] },
    exprSets: { mouth: ['expr_mouth_small', 'expr_mouth_round'] },
  },
  {
    id: 'props', name: '道具', role: '视频里的关键物品', from: 'EP1 · EP2 · EP3', height: 0.4,
    blurb: '电饭煲、黄金电饭煲、点赞牌、纸箱和绳子。',
    files: ['assets/characters/rice_cooker.glb', 'assets/characters/golden_cooker.glb', 'assets/characters/sign.glb', 'assets/characters/box.glb'],
    offsets: { 'assets/characters/sign.glb': [0, 0.1, 0] },
    anims: [['closed', '静置'], ['open', '打开锅盖']],
    once: ['open'],
  },
];

export const LINEUP = ['babies', 'bluefish', 'whale_big', 'dragon', 'doubao'];

export const EXPR_LABELS = {
  expr_eyes_open: '睁眼', expr_eyes_happy: '笑眼',
  expr_mouth_open: '张嘴笑', expr_mouth_small: '微笑', expr_mouth_round: '哦！', expr_mouth_cat: 'ω',
};
export const EXPR_GROUPS = { eyes: '眼睛', mouth: '嘴巴' };
