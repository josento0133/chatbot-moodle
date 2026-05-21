<?php
defined('MOODLE_INTERNAL') || die();

global $CFG;
require_once($CFG->dirroot . '/blocks/chatbot/block_chatbot.php');

class block_chatbot_test extends advanced_testcase {

    private function make_block(): block_chatbot {
        $block = new block_chatbot();
        $block->init();
        return $block;
    }

    private function call_b64url(block_chatbot $block, string $data): string {
        $ref = new ReflectionMethod($block, 'b64url');
        $ref->setAccessible(true);
        return $ref->invoke($block, $data);
    }

    private function call_generate_jwt(block_chatbot $block, int $user_id, string $secret): string {
        $ref = new ReflectionMethod($block, 'generate_jwt');
        $ref->setAccessible(true);
        return $ref->invoke($block, $user_id, $secret);
    }

    public function test_b64url_no_padding(): void {
        $block = $this->make_block();
        $result = $this->call_b64url($block, 'hello');
        $this->assertStringNotContainsString('=', $result);
    }

    public function test_b64url_replaces_plus_slash(): void {
        $block = $this->make_block();
        // force base64 chars that would produce + or /
        $result = $this->call_b64url($block, str_repeat("\xff\xfe", 16));
        $this->assertStringNotContainsString('+', $result);
        $this->assertStringNotContainsString('/', $result);
    }

    public function test_generate_jwt_structure(): void {
        $block = $this->make_block();
        $token = $this->call_generate_jwt($block, 42, 'test-secret');

        $parts = explode('.', $token);
        $this->assertCount(3, $parts, 'JWT must have three dot-separated parts');
    }

    public function test_generate_jwt_payload_user_id(): void {
        $block = $this->make_block();
        $token = $this->call_generate_jwt($block, 99, 'test-secret');

        $parts  = explode('.', $token);
        $padded = $parts[1] . str_repeat('=', (4 - strlen($parts[1]) % 4) % 4);
        $payload = json_decode(base64_decode(strtr($padded, '-_', '+/')), true);

        $this->assertEquals(99, $payload['user_id']);
        $this->assertArrayHasKey('exp', $payload);
        $this->assertGreaterThan(time(), $payload['exp']);
    }

    public function test_generate_jwt_signature_valid(): void {
        $block  = $this->make_block();
        $secret = 'my-test-secret';
        $token  = $this->call_generate_jwt($block, 1, $secret);

        $parts  = explode('.', $token);
        $expected_sig_raw = hash_hmac('sha256', $parts[0] . '.' . $parts[1], $secret, true);
        $expected_sig = rtrim(strtr(base64_encode($expected_sig_raw), '+/', '-_'), '=');

        $this->assertEquals($expected_sig, $parts[2]);
    }

    public function test_applicable_formats(): void {
        $block   = $this->make_block();
        $formats = $block->applicable_formats();

        $this->assertTrue($formats['course-view'] ?? false);
        $this->assertTrue($formats['site'] ?? false);
        $this->assertTrue($formats['my'] ?? false);
    }

    public function test_has_config(): void {
        $block = $this->make_block();
        $this->assertTrue($block->has_config());
    }

    public function test_instance_allow_multiple(): void {
        $block = $this->make_block();
        $this->assertFalse($block->instance_allow_multiple());
    }

    public function test_get_content_guest_returns_empty(): void {
        $this->resetAfterTest();
        $this->setGuestUser();

        $block = $this->make_block();
        $content = $block->get_content();

        $this->assertEmpty($content->text);
    }

    public function test_get_content_no_config_shows_message(): void {
        $this->resetAfterTest();
        $this->setAdminUser();

        // ensure settings are blank
        set_config('jwt_secret',   '',                  'block_chatbot');
        set_config('backend_url',  '',                  'block_chatbot');

        $block = $this->make_block();
        $content = $block->get_content();

        $this->assertStringContainsString('no está configurado', $content->text);
    }
}
