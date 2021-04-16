// Code generated by gen.py. DO NOT EDIT.

package expconf

import (
	"github.com/santhosh-tekuri/jsonschema/v2"
	"github.com/docker/docker/api/types"
	k8sV1 "k8s.io/api/core/v1"

	"github.com/determined-ai/determined/master/pkg/schemas"
)

func (e EnvironmentConfigV0) GetImage() EnvironmentImageMapV0 {
	if e.Image == nil {
		panic("You must call WithDefaults on EnvironmentConfigV0 before .GetImage")
	}
	return *e.Image
}

func (e EnvironmentConfigV0) GetEnvironmentVariables() EnvironmentVariablesMapV0 {
	if e.EnvironmentVariables == nil {
		panic("You must call WithDefaults on EnvironmentConfigV0 before .GetEnvironmentVariables")
	}
	return *e.EnvironmentVariables
}

func (e EnvironmentConfigV0) GetPorts() map[string]int {
	return e.Ports
}

func (e EnvironmentConfigV0) GetRegistryAuth() *types.AuthConfig {
	return e.RegistryAuth
}

func (e EnvironmentConfigV0) GetForcePullImage() bool {
	if e.ForcePullImage == nil {
		panic("You must call WithDefaults on EnvironmentConfigV0 before .GetForcePullImage")
	}
	return *e.ForcePullImage
}

func (e EnvironmentConfigV0) GetPodSpec() *k8sV1.Pod {
	return e.PodSpec
}

func (e EnvironmentConfigV0) GetAddCapabilities() []string {
	return e.AddCapabilities
}

func (e EnvironmentConfigV0) GetDropCapabilities() []string {
	return e.DropCapabilities
}

func (e EnvironmentConfigV0) WithDefaults() EnvironmentConfigV0 {
	return schemas.WithDefaults(e).(EnvironmentConfigV0)
}

func (e EnvironmentConfigV0) Merge(other EnvironmentConfigV0) EnvironmentConfigV0 {
	return schemas.Merge(e, other).(EnvironmentConfigV0)
}

func (e EnvironmentConfigV0) ParsedSchema() interface{} {
	return schemas.ParsedEnvironmentConfigV0()
}

func (e EnvironmentConfigV0) SanityValidator() *jsonschema.Schema {
	return schemas.GetSanityValidator("http://determined.ai/schemas/expconf/v0/environment.json")
}

func (e EnvironmentConfigV0) CompletenessValidator() *jsonschema.Schema {
	return schemas.GetCompletenessValidator("http://determined.ai/schemas/expconf/v0/environment.json")
}
