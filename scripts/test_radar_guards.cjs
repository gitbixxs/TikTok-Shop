const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const root = path.resolve(__dirname, '..', 'n8n_workflows');
const workflow = name => JSON.parse(fs.readFileSync(path.join(root, name + '.json'), 'utf8'));
const radar = workflow('TTS_01_Product_And_Outlier_Radar');
const architect = workflow('TTS_02_Script_And_Scene_Architect');
const code = name => radar.nodes.find(n => n.name === name).parameters.jsCode;
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor;
const items = values => ({ all: () => values.map(json => ({ json })) });

async function main() {
  for (const file of fs.readdirSync(root).filter(f => /^TTS_.*\.json$/.test(f))) {
    const w = JSON.parse(fs.readFileSync(path.join(root, file), 'utf8'));
    for (const node of w.nodes.filter(n => n.parameters.jsCode)) {
      new AsyncFunction('$input', '$', '$env', node.parameters.jsCode);
    }
  }

  const evaluate = new Function('$input', '$', code('Evaluate Account & Sunday Apify 5-Candidate Radar'));
  const discovery = evaluate({ first: () => ({ json: {} }) }, name => ({ all: () => [], isExecuted: name.startsWith('Sunday') }));
  const batches = discovery.filter(i => !i.json.stale_pause);
  assert.equal(batches.length, 3);
  const keywordLists = batches.map(i => JSON.parse(i.json.us_custom_body).searchKeywords);
  assert.deepEqual(keywordLists.map(k => k.length), [10, 10, 10]);
  assert.equal(new Set(keywordLists.flat()).size, 30);
  const loop = radar.nodes.find(n => n.name === 'Process US Keyword Batches');
  assert.equal(loop.parameters.batchSize, 1);
  assert.equal(loop.parameters.options.reset, false);
  assert.equal(radar.connections[loop.name].main[1][0].node, 'Apify US Bestseller Search (country=US)');
  assert.equal(radar.connections[loop.name].main[0][0].node, 'Score US Winners & Build DE Match Query');
  assert.equal(radar.connections['Apify US Bestseller Search (country=US)'].main[0][0].node, loop.name);

  const winners = Array.from({ length: 8 }, (_, i) => ({
    enKw: 'electric scrubber ' + i,
    kw: 'reinigungsbürste ' + i,
    title: 'Cordless Electric Spin Scrubber Cleaning Brush ' + i,
  }));
  const meta = {
    us_winners_json: JSON.stringify(winners),
    de_custom_body: JSON.stringify({ country: 'DE', searchKeywords: [] }),
  };
  const build = new Function('$input', code('Build Outlier Video Queries'));
  const batch = build(items([meta]));
  assert.equal(batch.length, 1);
  assert.equal(JSON.parse(batch[0].json.video_custom_body).searchQueries.length, 8);
  assert.throws(() => build(items([meta, meta])));
  assert.throws(() => build(items([{ ...meta, us_winners_json: JSON.stringify([...winners, winners[0]]) }])));
  assert.equal(build(items([{ ...meta, us_winners_json: '[]' }])).length, 0);
  assert.equal(JSON.parse(build(items([{ ...meta, us_winners_json: JSON.stringify([winners[0], winners[0]]) }]))[0].json.video_custom_body).searchQueries.length, 1);

  const score = new AsyncFunction('$input', '$', '$env', code('Score US Winners & Build DE Match Query'));
  const products = items([
    { product_id: '1', title: 'Cordless Electric Spin Scrubber Cleaning Set LED Display', price: 25, sold_count: 100, image_url: 'image' },
    { product_id: '2', title: 'Portable Handheld Steam Cleaner', price: 20, sold_count: 90, image_url: 'image' },
    { product_id: '3', title: 'Sturdy Stainless Steel BBQ Tongs', price: 20, sold_count: 80, image_url: 'image' },
  ]);
  const queryResponse = [
    { index: 0, en: 'electric spin scrubber', de: 'elektrische reinigungsbürste ausziehbar' },
    { index: 1, en: 'handheld steam cleaner', de: 'hand dampfreiniger zubehör' },
    { index: 2, en: 'stainless steel bbq tongs', de: 'grillzange edelstahl set' },
  ];
  const queryHelper = queries => ({ helpers: { httpRequest: async request => {
    assert.equal(JSON.parse(request.body).messages[1].content.includes('LED Display'), true);
    return { choices: [{ message: { content: JSON.stringify(queries) } }] };
  } } });
  const scoreContext = () => ({ all: () => [{ json: {} }] });
  const scored = await score.call(queryHelper(queryResponse), products, scoreContext, { HF_TOKEN: 'test-only' });
  const keywords = JSON.parse(scored[0].json.us_winners_json).map(w => w.kw);
  assert.deepEqual(keywords, queryResponse.map(q => q.de));
  assert.equal(scored[0].json.us_product_count, 3);
  await assert.rejects(() => score.call(queryHelper([]), products, scoreContext, { HF_TOKEN: 'test-only' }));
  await assert.rejects(() => score.call(queryHelper(queryResponse), products, scoreContext, {}));

  const map = new AsyncFunction('$input', '$', '$env', code('Map Outlier Videos To Winners'));
  const unsigned = 'https://api.apify.com/v2/key-value-stores/store/records/video-test.mp4';
  const video = {
    searchQuery: winners[2].enKw,
    text: 'This electric spin scrubber makes cleaning easier',
    playCount: 200000,
    videoMeta: { downloadAddr: unsigned, duration: 30 },
  };
  const relevance = selected => winners.map((_, index) => ({ index, video_index: index === 2 && selected ? 0 : null }));
  const relevanceHelper = response => ({ helpers: { httpRequest: async () => ({ choices: [{ message: { content: JSON.stringify(response) } }] }) } });
  const mapContext = () => ({ all: () => batch });
  const mapVideos = (videos, selected = true) => map.call(relevanceHelper(relevance(selected)), items(videos), mapContext, { HF_TOKEN: 'test-only' });
  const result = await mapVideos([video]);
  assert.equal(JSON.parse(result[0].json.winner_videos_json)[0].kw, winners[2].kw);
  assert.deepEqual(JSON.parse(result[0].json.de_custom_body).searchKeywords, [winners[2].kw]);
  for (const invalid of [
    { ...video, searchQuery: 'unrelated' },
    { ...video, playCount: 149999 },
    { ...video, isSlideshow: true },
    { ...video, videoMeta: { downloadAddr: unsigned, duration: 121 } },
    { ...video, videoMeta: { downloadAddr: 'https://example.com/pdp/product' } },
  ]) assert.equal((await mapVideos([invalid])).length, 0);
  assert.equal((await mapVideos([{ ...video, text: 'Dance viral trending' }], false)).length, 0);
  await assert.rejects(() => mapVideos([{ error: 'failed' }]));
  await assert.rejects(() => map.call(relevanceHelper([]), items([video]), mapContext, { HF_TOKEN: 'test-only' }));
  await assert.rejects(() => map.call(relevanceHelper(relevance(true)), items([video]), mapContext, {}));

  const requests = new Function('$input', code('Build Reference URL Requests'))(items([result[0].json]));
  const lookup = new URL(requests[0].json.lookup_url);
  assert.equal(lookup.searchParams.get('prefix'), 'video-test.mp4');
  assert.equal(lookup.searchParams.has('token'), false);
  const attach = new Function('$input', '$', code('Attach Public Reference URLs'));
  const context = () => ({ first: () => result[0] });
  assert.throws(() => attach(items([{ data: { items: [{ recordPublicUrl: unsigned }] } }]), context));
  const signed = unsigned + '?signature=test-fixture';
  const attached = attach(items([{ data: { items: [{ recordPublicUrl: signed }] } }]), context);
  assert.equal(JSON.parse(attached[0].json.winner_videos_json)[0].video_url, signed);

  const verify = new AsyncFunction('$input', '$', '$env', code('Verify DE Product And Reference Compatibility'));
  const candidates = items([{ product_name: 'Wrong lamp' }, { product_name: 'Cleaning brush' }]);
  const helper = decisions => ({ helpers: { httpRequest: async () => ({ choices: [{ message: { content: JSON.stringify(decisions) } }] }) } });
  const winContext = () => ({ first: () => ({ json: meta }) });
  const decisions = [{ index: 0, compatible: false }, { index: 1, compatible: true }];
  const accepted = await verify.call(helper(decisions), candidates, winContext, { HF_TOKEN: 'test-only' });
  assert.equal(accepted.length, 1);
  assert.deepEqual(accepted[0].pairedItem, { item: 1 });
  await assert.rejects(() => verify.call(helper([]), candidates, winContext, { HF_TOKEN: 'test-only' }));
  await assert.rejects(() => verify.call(helper(decisions), candidates, winContext, {}));

  const load = architect.nodes.find(n => n.name === 'Load Products');
  assert.equal(load.parameters.matchType, 'anyCondition');
  assert.deepEqual(load.parameters.filters.conditions.map(c => c.keyValue).sort(), ['approved', 'winner']);
  const scrape = radar.nodes.find(n => n.name === 'Apify US Outlier Video Scrape (clockworks)');
  assert.equal(scrape.executeOnce, true);
  assert.equal(scrape.retryOnFail, false);
  assert.equal(scrape.onError, 'stopWorkflow');
  assert.equal(radar.settings.saveExecutionProgress, true);
  console.log('PASS: JS syntax, batch cardinality, query dedupe/cap, product keywords, reference gates, signed URLs, compatibility decisions, item linking and approval filtering');
}

main().catch(error => { console.error(error); process.exitCode = 1; });
