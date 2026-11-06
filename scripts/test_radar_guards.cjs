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

  const score = new Function('$input', '$', code('Score US Winners & Build DE Match Query'));
  const scored = score(items([
    { product_id: '1', title: 'Cordless Electric Spin Scrubber Cleaning Set LED Display', price: 25, sold_count: 100, image_url: 'image' },
    { product_id: '2', title: 'Portable Handheld Steam Cleaner', price: 20, sold_count: 90, image_url: 'image' },
    { product_id: '3', title: 'Sturdy Stainless Steel BBQ Tongs', price: 20, sold_count: 80, image_url: 'image' },
  ]), () => ({ all: () => [{ json: {} }] }));
  const keywords = JSON.parse(scored[0].json.us_winners_json).map(w => w.kw);
  assert.equal(keywords[0], 'elektrische reinigungsbürste');
  assert.equal(keywords[1], 'dampfreiniger');
  assert.equal(keywords[2], 'küchenhelfer');

  const map = new Function('$input', '$', code('Map Outlier Videos To Winners'));
  const unsigned = 'https://api.apify.com/v2/key-value-stores/store/records/video-test.mp4';
  const video = {
    searchQuery: winners[2].enKw,
    text: 'This electric spin scrubber makes cleaning easier',
    playCount: 200000,
    videoMeta: { downloadAddr: unsigned, duration: 30 },
  };
  const mapVideos = videos => map(items(videos), () => ({ all: () => batch }));
  const result = mapVideos([video]);
  assert.equal(JSON.parse(result[0].json.winner_videos_json)[0].kw, winners[2].kw);
  assert.deepEqual(JSON.parse(result[0].json.de_custom_body).searchKeywords, [winners[2].kw]);
  for (const invalid of [
    { ...video, searchQuery: 'unrelated' },
    { ...video, playCount: 149999 },
    { ...video, isSlideshow: true },
    { ...video, text: 'Dance viral trending' },
    { ...video, text: 'Electric spin scrubber floor mop' },
    { ...video, videoMeta: { downloadAddr: 'https://example.com/pdp/product' } },
  ]) assert.equal(mapVideos([invalid]).length, 0);
  assert.throws(() => mapVideos([{ error: 'failed' }]));

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
