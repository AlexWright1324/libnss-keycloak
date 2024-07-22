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
                          command = "${libnss-keycloak}/bin/libnss-keycloak groupAll";
                        };

                        get_entry_by_gid = {
                          command = "${libnss-keycloak}/bin/libnss-keycloak groupID";
                        };

                        get_entry_by_name = {
                          command = "${libnss-keycloak}/bin/libnss-keycloak groupName";
                        };
                      };

                      env = {
                        groupID = "<$gid>";
                        groupName = "<$name>";
                        configFile = "/etc/libnss_shim/libnss-keycloak.toml";
                      };
                    };

                    passwd = {
                      functions = {
                        get_all_entries = {
                        command = "${libnss-keycloak}/bin/libnss-keycloak passwdAll";
                        };

                        get_entry_by_uid = {
                          command = "${libnss-keycloak}/bin/libnss-keycloak passwdID";
                        };

                        get_entry_by_name = {
                          command = "${libnss-keycloak}/bin/libnss-keycloak passwdName";
                        };
                      };
                      env = {
                        userID = "<$uid>";
                        userName = "<$name>";
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

              environment.etc."libnss_shim/libnss-keycloak.toml" = {
                source = cfg.configToml;
                user = "nscd";
                group = "nscd";
                mode = "0440";
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
                users.libnss-keycloak.enable = true;
                users.libnss-keycloak.configToml.source = ./config.toml;
                environment.systemPackages = with pkgs; [
                  htop
                ];
              })
            ];
          };
      };
  });
}