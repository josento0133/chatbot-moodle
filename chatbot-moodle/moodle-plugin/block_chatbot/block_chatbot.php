<?php
defined('MOODLE_INTERNAL') || die();

class block_chatbot extends block_base {

    public function init(): void {
        $this->title = get_string('pluginname', 'block_chatbot');
    }

    public function get_content(): stdClass {
        global $USER, $PAGE;

        if ($this->content !== null) {
            return $this->content;
        }

        $this->content         = new stdClass();
        $this->content->text   = '';
        $this->content->footer = '';

        if (!isloggedin() || isguestuser()) {
            return $this->content;
        }

        $secret      = get_config('block_chatbot', 'jwt_secret');
        $backend_url = get_config('block_chatbot', 'backend_url');

        if (empty($secret) || empty($backend_url)) {
            $this->content->text = '<p class="text-muted small">El asistente no está configurado. Contacta con el administrador.</p>';
            return $this->content;
        }

        $token = $this->generate_jwt((int) $USER->id, $secret);

        $PAGE->requires->js_call_amd('block_chatbot/chat', 'init', [[
            'token'      => $token,
            'backendUrl' => rtrim($backend_url, '/'),
            'userId'     => (int) $USER->id,
        ]]);

        $this->content->text = $this->render_container();
        return $this->content;
    }

    private function generate_jwt(int $user_id, string $secret): string {
        $header  = $this->b64url(json_encode(['alg' => 'HS256', 'typ' => 'JWT']));
        $payload = $this->b64url(json_encode([
            'user_id' => $user_id,
            'exp'     => time() + 3600,
            'iat'     => time(),
        ]));
        $sig = $this->b64url(hash_hmac('sha256', "$header.$payload", $secret, true));
        return "$header.$payload.$sig";
    }

    private function b64url(string $data): string {
        return rtrim(strtr(base64_encode($data), '+/', '-_'), '=');
    }

    private function render_container(): string {
        global $OUTPUT;
        return $OUTPUT->render_from_template('block_chatbot/chat', []);
    }

    public function applicable_formats(): array {
        return ['course-view' => true, 'site' => true, 'my' => true];
    }

    public function has_config(): bool {
        return true;
    }

    public function instance_allow_multiple(): bool {
        return false;
    }
}
