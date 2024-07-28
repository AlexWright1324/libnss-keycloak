{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-24.05";
    flake-parts.url = "github:hercules-ci/flake-parts";
    libnss_shim.url = "github:AlexWright1324/libnss_shim";
    poetry2nix.url = "github:nix-community/poetry2nix";
  };

  outputs = inputs:
    inputs.flake-parts.lib.mkFlake { inherit inputs; } ( { moduleWithSystem, ... }: rec {
      systems = [
        "x86_64-linux"
      ];

      perSystem = { self, pkgs, system, ... }:
        let
          poetry2nix = inputs.poetry2nix.lib.mkPoetry2Nix { inherit pkgs; };
        in
        {
          packages.default = poetry2nix.mkPoetryApplication {
              projectDir = ./.;
              preferWheels = true;
          };

          devShells.default = pkgs.mkShellNoCC {
            packages = with pkgs; [ 
              (poetry2nix.mkPoetryEnv { 
                projectDir = ./.; 
                preferWheels = true;
              })
              poetry
            ];
          };
        };

      flake = {
        nixosModules.default =  moduleWithSystem (
          perSystem @ { config }:
          { config, lib, pkgs, ... }:
          with lib;
          let
            libnss-keycloak = perSystem.config.packages.default;
            cfg = config.users.libnss-keycloak;
            socketPath = "/var/run/libnss-keycloak/libnss-keycloak.sock";
          in {
            imports = [ inputs.libnss_shim.nixosModules.default ];

            options.users.libnss-keycloak = {
              enable = mkEnableOption "Enables libnss-keycloak";

              configToml = mkOption rec {
                type = types.path;
                default = "";
                example = default;
                description = "libnss-keycloak config.toml";
              };
            };

            config = mkIf cfg.enable {
              users.libnss_shim = {
                enable = true;

                configJson = {
                  databases = {
                    group = {
                      functions = {
                        get_all_entries = {
                          command = "/etc/libnss_shim/libnss-keycloak-groupAll.sh";
                        };

                        get_entry_by_gid = {
                          command = "/etc/libnss_shim/libnss-keycloak-groupID.sh";
                        };

                        get_entry_by_name = {
                          command = "/etc/libnss_shim/libnss-keycloak-groupName.sh";
                        };
                      };

                      env = {
                        id = "<$gid>";
                        name = "<$name>";
                        configFile = "/etc/libnss_shim/libnss-keycloak.toml";
                      };
                    };

                    passwd = {
                      functions = {
                        get_all_entries = {
                          command = "/etc/libnss_shim/libnss-keycloak-passwdAll.sh";
                        };

                        get_entry_by_uid = {
                          command = "/etc/libnss_shim/libnss-keycloak-passwdID.sh";
                        };

                        get_entry_by_name = {
                          command = "/etc/libnss_shim/libnss-keycloak-passwdName.sh";
                        };
                      };
                      env = {
                        id = "<$uid>";
                        name = "<$name>";
                        configFile = "/etc/libnss_shim/libnss-keycloak.toml";
                      };
                    };
                  };
                  
                  # This might not work
                  env = {
                    configFile = "/etc/libnss_shim/libnss-keycloak.toml";
                  };
                };
              };

              # Hacky method
              systemd.services.nscd.path = with pkgs; [ bash netcat ];

              systemd.services.libnss-keycloak = {
                enable = true;
                description = "libnss-keycloak nsswitch module using libnss_shim";
                wants = [ "network-online.target" ];
                after = [ "network-online.target" ];
                environment = {
                  PYTHONUNBUFFERED = "1";
                  configFile = "/etc/libnss_shim/libnss-keycloak.toml";
                  inherit socketPath;
                };
                serviceConfig = {
                  Type = "simple";
                  User = "nscd";
                  Group = "nscd";
                  ExecStart = "${libnss-keycloak}/bin/libnss-keycloak";
                  RuntimeDirectory = "libnss-keycloak";
                };
              };

              environment.etc = let
                  mode = "0555";
                in
                {
                "libnss_shim/libnss-keycloak.toml" = {
                  source = cfg.configToml;
                  user = "nscd";
                  group = "nscd";
                  mode = "0440";
                };
                "libnss_shim/libnss-keycloak-passwdAll.sh" = {
                  text = ''
                    #!/bin/sh
                    echo -n "passwdAll" | nc -U ${socketPath} 2>/dev/null
                  '';
                  inherit mode;
                };
                "libnss_shim/libnss-keycloak-groupAll.sh" = {
                  text = ''
                    #!/bin/sh
                    echo -n "groupAll" | nc -U ${socketPath} 2>/dev/null
                  '';
                  inherit mode;
                };
                "libnss_shim/libnss-keycloak-passwdID.sh" = {
                  text = ''
                    #!/bin/sh
                    echo -n "passwdID $id" | nc -U ${socketPath} 2>/dev/null
                  '';
                  inherit mode;
                };
                "libnss_shim/libnss-keycloak-groupID.sh" = {
                  text = ''
                    #!/bin/sh
                    echo -n "groupID $id" | nc -U ${socketPath} 2>/dev/null
                  '';
                  inherit mode;
                };
                "libnss_shim/libnss-keycloak-passwdName.sh" = {
                  text = ''
                    #!/bin/sh
                    echo -n "passwdName $name" | nc -U ${socketPath} 2>/dev/null
                  '';
                  inherit mode;
                };
                "libnss_shim/libnss-keycloak-groupName.sh" = {
                  text = ''
                    #!/bin/sh
                    echo -n "groupName $name" | nc -U ${socketPath} 2>/dev/null
                  '';
                  inherit mode;
                };
              };
            };
        });

        # sudo nixos-container create keycloak --flake path:.#test
        nixosConfigurations.test =
          inputs.nixpkgs.lib.nixosSystem {
            system = "x86_64-linux";
            modules = [
              flake.nixosModules.default
              ({ pkgs, ... }: {
                boot.isContainer = true;
                networking.firewall.enable = false;
                users.libnss-keycloak.enable = true;
                users.libnss-keycloak.configToml = ./config.toml;
                environment.systemPackages = with pkgs; [
                  htop
                ];
                system.stateVersion = "24.05";
              })
            ];
          };
      };
  });
}