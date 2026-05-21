<?php
defined('MOODLE_INTERNAL') || die();

if ($ADMIN->fulltree) {
    $settings->add(new admin_setting_configtext(
        'block_chatbot/backend_url',
        get_string('backend_url', 'block_chatbot'),
        get_string('backend_url_desc', 'block_chatbot'),
        'http://localhost:8000',
        PARAM_URL
    ));

    $settings->add(new admin_setting_configpasswordunmask(
        'block_chatbot/jwt_secret',
        get_string('jwt_secret', 'block_chatbot'),
        get_string('jwt_secret_desc', 'block_chatbot'),
        ''
    ));

    $settings->add(new admin_setting_configtext(
        'block_chatbot/daily_limit',
        get_string('daily_limit', 'block_chatbot'),
        get_string('daily_limit_desc', 'block_chatbot'),
        '50',
        PARAM_INT
    ));
}
