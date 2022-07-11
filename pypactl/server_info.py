class ServerInfo:
    def __init__(self):
        self.package_name = None
        self.package_version = None
        self.user_name = None
        self.host_name = None
        self.default_sample_spec = None
        self.default_sink = None
        self.default_source = None
        self.cookie = None
        self.default_channel_map = None


    def __repr__(self):
        return f"<ServerInfo package_name={self.package_name} package_version={self.package_version} user_name={self.user_name} host_name={self.host_name} default_sample_spec={self.default_sample_spec} default_sink={self.default_sink} default_source={self.default_source} cookie={self.cookie} default_channel_map={self.default_channel_map}>"
